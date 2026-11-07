"""Export one deployed student to ONNX (FP32 and static INT8) and measure it on this machine.

Usage:
  .venv/Scripts/python.exe -I scripts/export_benchmark.py --checkpoint checkpoints/main/A_fold0_gate_s0.pt
  .venv/Scripts/python.exe -I scripts/export_benchmark.py --checkpoint checkpoints/main/A_fold0_ce_ord_s0.pt
  .venv/Scripts/python.exe -I scripts/export_benchmark.py --random      # pipeline check, untrained weights

All student variants of one front-end share one architecture, so size and latency describe the
architecture, not the training method. The front-end runs outside the ONNX graph and is timed separately:
the log spectrum (Hz axis) as a NumPy twin, the log order spectrum as the PyTorch implementation on CPU.
Calibration uses training windows only (Protocol A fold 0); parity uses validation windows; accuracy and
decision agreement with the evaluation pipeline (GPU front-end, bf16 inference, as in results/main) are
computed once on the fold-0 test windows of the same checkpoint.
Outputs: exports/<tag>_{fp32,int8}.onnx, results/deploy/benchmark_<tag>.json
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import re
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

ROOT = Path(__file__).resolve().parents[1]
CACHE = Path("D:/bahrain-data/cache/paderborn/v2")
EXP, OUT = ROOT / "exports", ROOT / "results/deploy"
N_IN = {"hz": 2001, "ord": 897}


def numpy_logspec(x: np.ndarray, hann: np.ndarray, n_keep: int = 2001) -> np.ndarray:
    """NumPy twin of LogSpectrumFrontEnd followed by per-window standardisation (deployment preprocessing)."""
    x = x.astype(np.float32)
    mag = np.abs(np.fft.rfft((x - x.mean()) * hann))[:n_keep]
    y = 20 * np.log10(mag + mag.max() * 1e-7)
    return ((y - y.mean()) / (y.std() + 1e-6)).astype(np.float32)


def standardise(y: torch.Tensor) -> torch.Tensor:
    return (y - y.mean(-1, keepdim=True)) / (y.std(-1, unbiased=False, keepdim=True) + 1e-6)


class LogitsOnly(torch.nn.Module):
    def __init__(self, student):
        super().__init__()
        self.s = student

    def forward(self, x):
        return self.s(x)[0]


def windows_for(bearings, rows_idx, cur, stride, n_max, seed):
    rng = np.random.default_rng(seed)
    sel = rows_idx[rows_idx["bearing"].isin(bearings)]
    items = [(int(r.cache_row), s, int(r.label)) for r in sel.itertuples() for s in range(0, int(r.valid_current_8000) - 4000 + 1, stride)]
    if n_max and len(items) > n_max:
        items = [items[i] for i in rng.choice(len(items), n_max, replace=False)]
    return items


def lat(fn, n_warm=100, n=2000):
    for _ in range(n_warm):
        fn()
    t = np.empty(n)
    for i in range(n):
        t0 = time.perf_counter()
        fn()
        t[i] = time.perf_counter() - t0
    return {"median_ms": float(np.median(t) * 1e3), "p95_ms": float(np.percentile(t, 95) * 1e3), "n": n}


def softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(1, keepdims=True))
    return e / e.sum(1, keepdims=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--checkpoint", type=Path)
    ap.add_argument("--random", action="store_true")
    ap.add_argument("--frontend", choices=["hz", "ord"], default=None, help="default: 'ord' if the checkpoint name has _ord_")
    args = ap.parse_args()
    import onnx
    import onnxruntime as ort
    from onnxruntime.quantization import CalibrationDataReader, QuantFormat, QuantType, quantize_static
    from onnxruntime.quantization.shape_inference import quant_pre_process
    from sklearn.metrics import f1_score

    from cmkd.models import Student, count_parameters
    from cmkd.models.frontend import LogOrderSpectrumFrontEnd, LogSpectrumFrontEnd

    tag = args.checkpoint.stem if args.checkpoint else "random"
    kind = args.frontend or ("ord" if "_ord_" in tag else "hz")
    n_in = N_IN[kind]
    EXP.mkdir(exist_ok=True)
    OUT.mkdir(parents=True, exist_ok=True)
    student = Student(None, stem_stride=2)
    if not args.random:
        student.load_state_dict(torch.load(args.checkpoint, map_location="cpu", weights_only=True))
    student.eval()
    model = LogitsOnly(student).eval()
    fe = LogSpectrumFrontEnd(8000, 4000) if kind == "hz" else LogOrderSpectrumFrontEnd(8000, 4000)
    hann = fe.hann.numpy() if kind == "hz" else None

    def torch_prep(raw: np.ndarray, device="cpu") -> np.ndarray:
        with torch.no_grad():
            y, _ = fe.to(device)(torch.tensor(raw, device=device))
            return standardise(y).cpu().numpy().astype(np.float32)

    def deploy_prep(raw: np.ndarray) -> np.ndarray:
        """The preprocessing that runs in deployment: NumPy twin (hz) or PyTorch CPU (ord)."""
        if kind == "hz":
            return np.stack([numpy_logspec(w, hann) for w in raw])
        return np.concatenate([torch_prep(raw[i:i + 256]) for i in range(0, len(raw), 256)])

    idx = pd.read_csv(CACHE / "index.csv")
    idx["label"] = idx["class3"].map({"healthy": 0, "outer": 1, "inner": 2})
    cur = np.load(CACHE / "current_8000.npy", mmap_mode="r")
    fold = json.loads((ROOT / "manifests/splits/protocol_A.json").read_text())["folds"][0]
    calib = windows_for(fold["train"], idx, cur, 2000, 512, 1)
    val = windows_for(fold["validation"], idx, cur, 4000, 1024, 2)
    test = windows_for(fold["test"], idx, cur, 4000, None, 3)
    raw_of = lambda items: np.stack([np.asarray(cur[r, s:s + 4000], dtype=np.float32) for r, s, _ in items])
    prep = lambda items: deploy_prep(raw_of(items))[:, None, :]

    # Parity of deployment preprocessing with the training/evaluation front-end (GPU) and with PyTorch CPU,
    # per input value and at the level of the FP32 model's window decisions (validation windows)
    raw_val = raw_of(val)
    y_dep = deploy_prep(raw_val)
    refs = {"torch_cpu": torch_prep(raw_val)}
    if torch.cuda.is_available():
        refs["torch_gpu_eval_path"] = torch_prep(raw_val, "cuda")
    fe.to("cpu")
    f_bins = np.arange(n_in) * (2.0 if kind == "hz" else 1 / 28)
    stop = f_bins > (3200 if kind == "hz" else np.inf)
    with torch.no_grad():
        dec_dep = model(torch.tensor(y_dep[:, None, :])).numpy()
        prep_parity = {}
        for name, y_ref in refs.items():
            d = np.abs(y_ref - y_dep)
            dec_ref = model(torch.tensor(y_ref[:, None, :])).numpy()
            prep_parity[name] = {"max_abs": float(d.max()), "p99_9_abs": float(np.percentile(d, 99.9)),
                                 "median_abs": float(np.median(d)),
                                 "max_abs_outside_decimation_stopband": float(d[:, ~stop].max()),
                                 "window_decision_agreement": float(np.mean(dec_ref.argmax(1) == dec_dep.argmax(1))),
                                 "max_abs_logit_diff": float(np.max(np.abs(dec_ref - dec_dep)))}

    fp32 = EXP / f"{tag}_fp32.onnx"
    torch.onnx.export(model, torch.zeros(1, 1, n_in), fp32, input_names=["spec"], output_names=["logits"],
                      dynamic_axes={"spec": {0: "batch"}, "logits": {0: "batch"}}, opset_version=17, dynamo=False)
    onnx.checker.check_model(onnx.load(fp32))

    class Reader(CalibrationDataReader):
        def __init__(self, data):
            self.it = iter([{"spec": d[None]} for d in data])

        def get_next(self):
            return next(self.it, None)

    int8 = EXP / f"{tag}_int8.onnx"
    pre = EXP / f"{tag}_fp32_preprocessed.onnx"
    quant_pre_process(str(fp32), str(pre), skip_symbolic_shape=True)
    quantize_static(str(pre), str(int8), Reader(prep(calib)), quant_format=QuantFormat.QDQ,
                    activation_type=QuantType.QUInt8, weight_type=QuantType.QInt8, per_channel=True)
    ops = {}
    for n in onnx.load(int8).graph.node:
        ops[n.op_type] = ops.get(n.op_type, 0) + 1

    xv = y_dep[:, None, :]
    with torch.no_grad():
        ref = model(torch.tensor(xv)).numpy()
    res = {"hardware": {"cpu": platform.processor(), "machine": platform.machine(), "logical_cpus": os.cpu_count(),
                        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None},
           "software": {"python": platform.python_version(), "numpy": np.__version__, "torch": torch.__version__,
                        "onnxruntime": ort.__version__, "onnx": onnx.__version__},
           "checkpoint": str(args.checkpoint) if args.checkpoint else "random-init (pipeline check only)",
           "frontend": kind, "input_bins": n_in,
           "deploy_preprocessing": "NumPy twin of LogSpectrumFrontEnd" if kind == "hz" else "PyTorch LogOrderSpectrumFrontEnd on CPU",
           "parameters_deployed": count_parameters(student) - sum(p.numel() for p in student.proj.parameters()),
           "file_bytes": {"fp32": fp32.stat().st_size, "int8": int8.stat().st_size},
           "int8_graph_op_counts": ops, "preprocessing_parity": prep_parity,
           "decision_timing_note": "one window needs 0.5 s of acquisition; a recording decision needs 4.0 s; latencies below exclude acquisition"}
    for name, path in (("fp32", fp32), ("int8", int8)):
        for threads in (1, 4):
            so = ort.SessionOptions()
            so.intra_op_num_threads, so.inter_op_num_threads = threads, 1
            sess = ort.InferenceSession(str(path), so, providers=["CPUExecutionProvider"])
            out = sess.run(None, {"spec": xv})[0]
            one = xv[:1]
            res.setdefault(name, {})[f"cpu_threads{threads}"] = lat(lambda: sess.run(None, {"spec": one}))
            res[name]["max_abs_diff_vs_torch_fp32"] = float(np.max(np.abs(out - ref)))
            res[name]["argmax_agreement_vs_torch_fp32"] = float(np.mean(out.argmax(1) == ref.argmax(1)))
    raw1 = raw_val[:1]
    torch.set_num_threads(1)
    res["preprocessing_cpu_threads1"] = lat((lambda: numpy_logspec(raw1[0], hann)) if kind == "hz" else (lambda: torch_prep(raw1)))
    if kind == "hz":
        res["preprocessing_torch_cpu_threads1"] = lat(lambda: torch_prep(raw1))
    torch.set_num_threads(4)
    one_t = torch.tensor(xv[:1])
    with torch.no_grad():
        res["torch_fp32_cpu_threads4"] = lat(lambda: model(one_t))
        if torch.cuda.is_available():
            mg = model.to("cuda")
            g = one_t.to("cuda")

            def run_gpu():
                mg(g)
                torch.cuda.synchronize()
            res["torch_fp32_gpu"] = lat(run_gpu)
            model.to("cpu")

    m = re.fullmatch(r"A_fold0_(.+)_s(\d)", tag)
    if not args.random and m:
        xt = prep(test)
        lab = np.array([l for _, _, l in test])
        key = pd.MultiIndex.from_arrays([[r for r, _, _ in test], [s // 4000 for _, s, _ in test]])
        ev = np.load(ROOT / "results/main/A/fold0" / m.group(1) / f"seed{m.group(2)}" / "predictions_test.npz")
        ev_df = pd.DataFrame(ev["probs"], index=pd.MultiIndex.from_arrays([ev["recording"], ev["window_no"]]))
        common = key.intersection(ev_df.index)
        pos = key.get_indexer(common)
        p_eval = ev_df.loc[common].to_numpy()
        rec = np.asarray(common.get_level_values(0))
        y = lab[pos]

        def rec_level(p):
            df = pd.DataFrame(p).assign(rec=rec, lab=y).groupby("rec").mean()
            return df[[0, 1, 2]].to_numpy().argmax(1), df["lab"].astype(int).to_numpy()

        d_eval, y_rec = rec_level(p_eval)
        res["evaluation_pipeline"] = {"fold0_test_recording_macro_f1": float(f1_score(y_rec, d_eval, labels=[0, 1, 2], average="macro")),
                                      "matched_windows": int(len(common)), "deploy_windows": int(len(key)),
                                      "evaluation_windows": int(len(ev_df))}
        for name, path in (("fp32", fp32), ("int8", int8)):
            sess = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
            pr = softmax(np.concatenate([sess.run(None, {"spec": xt[i:i + 512]})[0] for i in range(0, len(xt), 512)]))[pos]
            d_rec, _ = rec_level(pr)
            res[name]["fold0_test_recording_macro_f1"] = float(f1_score(y_rec, d_rec, labels=[0, 1, 2], average="macro"))
            res[name]["window_decision_agreement_vs_evaluation"] = float(np.mean(pr.argmax(1) == p_eval.argmax(1)))
            res[name]["recording_decision_agreement_vs_evaluation"] = float(np.mean(d_rec == d_eval))
    out_json = OUT / ("benchmark_random_check.json" if args.random else f"benchmark_{tag}.json")
    out_json.write_text(json.dumps(res, indent=1), encoding="utf-8")
    show = ("file_bytes", "parameters_deployed", "preprocessing_parity", "evaluation_pipeline")
    print(json.dumps({k: res[k] for k in show if k in res}, indent=1))
    for name in ("fp32", "int8"):
        print(name, {k: v for k, v in res[name].items() if not isinstance(v, dict)}, "| cpu1", res[name]["cpu_threads1"]["median_ms"], "ms")
    print("prep cpu1", res["preprocessing_cpu_threads1"]["median_ms"], "ms ->", out_json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
