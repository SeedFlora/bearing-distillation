# Experimental protocol — DRAFT v0.1 (not frozen)

Status: draft written 2026-11-07 after the data audit and split freeze, before
any model was trained. It becomes v1.0 (frozen) after the development pilot,
when the items marked **[pilot rule]** are resolved by the rules stated here.
Any later change is appended as a dated amendment with its reason.

## 1. Question and hypotheses

Does a small current-only student benefit from a fixed teacher that also sees
vibration, and does weighting the feature-alignment term by an independently
estimated transfer-difficulty proxy improve that benefit on unseen bearings and
unseen operating conditions?

- H1 (cross-modal KD): ungated feature KD from the multimodal teacher raises
  recording-level macro-F1 of the current-only student relative to the
  identical CE-only student.
- H2 (gate): the out-of-group bridge-residual gate raises macro-F1 relative to
  ungated feature KD, and relative to gates that keep the weight distribution
  but remove the out-of-group estimate (shuffled gate; in-sample residual
  gate; non-grouped cross-fitting gate).

The residual is a proxy for transfer difficulty. A large residual may reflect
modality mismatch, bridge capacity, noise or finite data; it is not evidence
that information is physically absent from current.

## 2. Data

Primary: Paderborn KAt Bearing DataCenter (CC BY-NC 4.0), 32 archives,
downloaded 2026-11-07 (hashes: `manifests/provenance/paderborn_downloads.tsv`).
Primary three-class population (`manifests/splits/paderborn_population.csv`):
27 bearings — healthy 6 (K001–K006), outer 12 (KA01, KA03–KA09, KA15, KA16,
KA22, KA30), inner 9 (KI01, KI03, KI05, KI07, KI08, KI16, KI17, KI18, KI21);
2,155 recordings after exclusions (decisions D04, D05).
Excluded from the primary population: KB23, KB24, KB27 (combined); KI04, KI14
(sources conflict; sensitivity analysis §9.3).

The independent experimental unit is the physical bearing. Recordings (20 per
bearing and condition) and windows are repeated measurements of that unit.

## 3. Input contract and preprocessing

- Student input: `phase_current_1` only. Teacher input: `phase_current_1` and
  `vibration_1` over the same physical interval. Nothing else (speed, torque,
  force, temperature, file name, bearing ID, date, split ID) enters any model.
- Each recording is linearly interpolated on its own time vector onto a
  uniform 64-kHz grid, truncated to 4.0 s, low-pass filtered and decimated
  (polyphase FIR, Kaiser β=8) to the current rate and to 32 kHz for vibration
  (decision D06; development spectra in `reports/figures/dev_spectra.pdf`).
- Current rate **[pilot rule]**: 8 kHz or 16 kHz (both exclude the ~16-kHz
  inverter switching band). Rule: choose the rate with the higher mean pilot
  validation recording-level macro-F1 of the CE-only student over the two
  pilot folds; if the difference is below 1 percentage point, choose 8 kHz.
- Window: 0.5 s (4,000 current samples at 8 kHz; 16,000 vibration samples).
  Evaluation windows are non-overlapping from the start of each recording
  (8 per recording; 7 for the two recordings shorter than 4 s). Training
  windows use a stride of 0.25 s (50% overlap, explicit).
- Fixed per-window standardisation (zero mean, unit variance) of each channel;
  no dataset-level statistic is fitted, so there is nothing to leak.

## 4. Splits (frozen; `manifests/splits/`, SHA-256 in `SPLITS_SHA256.txt`)

Seed 20261107; stratified by class x damage origin; metadata only.

- Development pool (never test evidence): K001, K005, KA07, KA16, KI01, KI16.
  Pilot folds: two swaps of one bearing per class for training and the other
  for validation.
- Protocol A (primary, unseen bearings): three outer folds over the 21
  non-development bearings (7 test bearings each). For each fold, 5 validation
  bearings (1 healthy, 1+1 outer, 1+1 inner by origin) and 15 training bearings;
  training bearings split into 3 bridge folds, each containing all classes.
  All conditions of a bearing follow its assignment.
- Protocol B (unseen operating condition): for each of the four conditions,
  fit on all 27 bearings under the three other conditions; test on the 21
  non-development bearings under the held-out condition. Claims are about
  previously observed bearings under a new condition. Hyper-parameters and the
  epoch budget are selected by inner leave-one-source-condition-out validation;
  the held-out condition never enters teacher training, bridge fitting, gate
  fitting, checkpoint or hyper-parameter selection.
- Protocol C (optional, joint): declared in `protocol_C.json`; run only after
  A and B, and only if its design is recorded here before inspection.

## 5. Models

- Teacher: two-branch 1D residual CNN (one branch per modality), feature
  fusion, task bottleneck (d=64), linear classifier. Trained on source
  training bearings, checkpoint selected on source validation, then frozen.
  Targets extracted in eval mode under `torch.no_grad()` and cached with
  (dataset, recording, window, preprocessing hash, teacher checkpoint hash,
  view id).
- Student: depthwise-separable 1D CNN with classifier; identical architecture,
  data and budget for every method. A linear projection to d=64 exists only
  during training and is discarded at inference.
- Bridge: current-only 1D CNN regressor of the normalised teacher bottleneck
  (small capacity by default; one larger capacity in the bounded mechanism
  check).

## 6. Methods compared (identical student)

1. CE-only. 2. Logit KD (temperature and weight tuned, §7). 3. Ungated feature
KD (Huber on L2-normalised features). 4. Teacher-confidence gate. 5. SAAMask
re-implemented from the published algorithm (Jo and Um, IEEE Access 2026,
Eqs. 3–7 and Algorithm 1: mask built once after warm-up from the student's own
squared residual, top-20% dimensions per sample suppressed); details the paper
does not specify are listed as adaptation choices. 6. Shuffled residual gate
(within class and source condition). 7. Bridge + classification head
(auxiliary-model control, reported separately with its own size and cost).
8. Proposed: out-of-group bridge-residual gate, class-normalised.

Bounded mechanism controls (Protocol A, all three folds, three seeds unless a
smaller subset is stated before running): (i) in-sample student-residual
sample gate (no cross-fitting); (ii) bridges cross-fitted with random,
non-grouped folds; (iii) current-only teacher of the same size (vibration
branch removed) with ungated feature KD; (iv) larger bridge; (v) gate without
class normalisation.

## 7. Tuning budget and stopping

Predeclared and identical in size across KD variants:
- Optimiser AdamW, cosine schedule, batch 256, maximum 40 epochs; checkpoint =
  best validation recording-level macro-F1; patience 8 epochs.
- Logit KD: T in {2, 4} x weight in {0.5, 1.0} (4 settings).
- Feature KD variants: lambda in {0.5, 1.0} (2 settings); gate: tau in
  {median, 2 x median of training residuals} x epsilon in {0.05, 0.2}
  (4 settings), chosen on validation only.
- Selection uses validation bearings (Protocol A) or the inner held-out source
  condition (Protocol B); test data are never used for any choice.

## 8. Seeds and what they vary

Three seeds (0, 1, 2) vary student initialisation and data order. Teacher and
bridges are trained once per outer fold (seed 0) and held fixed, so seed
variation does not represent full-pipeline variability; this is stated in the
paper. Increasing to five seeds requires a written reason here first.

## 9. Evaluation

### 9.1 Primary endpoint
Recording-level macro-F1 on Protocol A test bearings, pooled over the three
outer folds: class probabilities are averaged over the evaluation windows of a
recording (fixed rule) and the arg-max is the decision. One decision therefore
uses 4.0 s of current (3.5 s for two short recordings). Window-level macro-F1,
balanced accuracy, class-wise recall, confusion matrices and per-condition
results are secondary.

### 9.2 Statistics
- Negative transfer = metric(method) minus metric(CE-only) on the same fold
  and seed.
- Uncertainty: percentile bootstrap over test bearings (resampled within
  class, 10,000 replicates), applied to the seed-averaged paired differences.
  Seeds are reported separately and never treated as independent specimens.
- Primary family (Holm-adjusted): proposed vs CE-only; proposed vs ungated
  feature KD; proposed vs SAAMask; proposed vs shuffled gate. With 21 test
  bearings, claims are stated as effect sizes with intervals; significance
  language is used only where the bearing-level interval supports it.

### 9.3 Predeclared diagnostics
- Campaign diagnostic: error rates of damaged test bearings recorded in 2015
  versus 2014, and of healthy test bearings (all 2015, all IBU) (D08).
- KI04/KI14 sensitivity: share of their recordings predicted inner, outer and
  healthy by each Protocol A model (reference label: inner, dominant damage).
- Residual/weight distributions by class and condition; association between a
  sample's gate weight and the student's held-out error (descriptive).

## 10. Deployment measurement
FP32 ONNX export with parity check against PyTorch outputs on validation
windows; INT8 static quantisation with ONNX Runtime using training-window
calibration only; operators, fallbacks and versions recorded. Latency at batch
size 1 after warm-up with fixed threads on the available laptop CPU (Intel
Core i7-12700H) and GPU; reported as laptop measurements. No edge device is
connected; edge results remain unmeasured.

## Amendment A1 (2026-11-07, before any pilot run): new architecture factor and pilot plan

Requested by the author: test a new model architecture. Added factor:
**electrical-order front-end (OF)** for the student (`src/cmkd/models/frontend.py`).
The supply frequency is estimated from each current window (Hann FFT peak in
20–200 Hz, parabolic interpolation), the window is band-limited to 32 x f_e and
resampled to 28 electrical cycles x 64 samples per cycle; the DS-CNN then uses
a stem stride of 4. Rationale: the drive is a PMSM with 4 pole pairs, so
f_e = 4 x shaft frequency (checked on development bearings: 59.99 +/- 0.14 Hz at
900 rpm, 100.0 +/- 0.2 Hz at 1500 rpm), and bearing defect frequencies sit at
fixed electrical orders. Current-only; no tachometer or metadata.

- **H3**: OF raises recording-level macro-F1 of the CE-only student when the
  900-rpm setting is held out (Protocol B, target N09_M07_F10) and is neutral
  for the other held-out settings and for Protocol A.
- Main design becomes 2 x 2 for the core methods: {time-domain DS-CNN, OF
  DS-CNN} x {CE-only, proposed gate} (plus ungated feature KD for both). All
  other methods use the time-domain student. Teacher and bridges are shared.

Development pilot (development bearings only; one seed; settings fixed here):
- Pilot-A, unseen bearing, two swap folds: P1 train {K001, KA07, KI16} /
  evaluate {K005, KA16, KI01}; P2 the reverse. Teacher; bridges cross-fitted by
  **condition** (bearing groups with every class are impossible with three
  training bearings; pilot-only variant); students CE@8 kHz, CE@16 kHz, CE-OF,
  ungated feature KD@8 kHz, residual gate@8 kHz (lambda 1, tau = median
  residual, epsilon 0.2, class-normalised). Max 30 epochs, patience 8,
  selection on the pilot evaluation bearings (pilot only).
- Pilot-B, unseen speed: fit on the six development bearings under the three
  1500-rpm settings, evaluate on the same bearings at 900 rpm; bridges
  cross-fitted over two bearing groups {K001, KA07, KI01} / {K005, KA16, KI16};
  students CE@8 kHz, CE-OF, feature KD@8 kHz, gate@8 kHz, feature KD-OF; fixed
  30 epochs, last epoch kept (the target setting is never used for selection).
- Added before the pilot's student runs (after the first teacher scored a
  recording-level macro-F1 of 0.218 on P1): Pilot-S, a learnability check on
  the same six development bearings with recordings 1–14 for fitting and
  15–20 for evaluation, and the teacher's score on its own training bearings.
  Both only diagnose the implementation; neither is generalisation evidence.
- Decisions taken from the pilot: current rate (rule of §3), teacher
  competence (teacher must beat chance clearly on Pilot-A), epoch budget.
  OF stays in the main design whatever its pilot score, because H3 is tested
  only on non-development bearings.

## Amendment A2 (2026-11-07, after the first pilot, before the representation runs)

Pilot finding: CE-only current students barely fit even their own training
windows (Pilot-S training loss 1.10 -> 1.06 in 15 epochs; 0.87 after 30), while
the vibration-aware teacher fits within two epochs. A precision check rejected
bfloat16 as the cause (fp32 and bf16 runs identical; `results/pilot/diag_precision.json`).
The supply fundamental lies about 70 dB above the median 150–2000 Hz level, so a
standardised waveform is almost a pure sinusoid. Candidate fixed per-window
representations for the student, compared on development bearings only:
waveform (Hz axis), order-resampled waveform, log-magnitude spectrum (Hz axis,
0–4 kHz) and log-magnitude order spectrum (orders 0–32, resolution 1/28).

Rule (fixed before running): the representation *type* (waveform vs
log-magnitude spectrum) is chosen by the mean CE-only recording macro-F1 over
Pilot-S and the two Pilot-A folds, averaged over the Hz and order variants;
ties within 0.02 favour the waveform. Pilot-B (900 rpm) is reported but not
used for the choice. H3 then compares the Hz and order variants of the chosen
type on non-development bearings.

## Amendment A3 (2026-11-07, freeze; before any main run)

Pilot outcomes applied by the predeclared rules: current rate 8 kHz (CE-only
waveform students at 8 vs 16 kHz on Pilot-A: 0.302 vs 0.304, difference below
1 point); student representation = log-magnitude spectrum (A2 rule: 0.402 vs
0.355); epoch budget 40 with patience 10 (students were still improving at 30).
Teacher input unchanged (current and vibration waveforms). Bridges use the same
fixed representation as the student variant they serve.

Protocol A methods and tuning (seed 0 on validation bearings; seeds 1 and 2
reuse the chosen setting): CE; logit KD (T in {2,4} x weight in {0.5,1});
ungated feature KD (lambda in {0.5,1}); teacher-confidence gate (lambda);
SAAMask re-implementation (lambda; mask after 4 warm-up epochs); proposed gate
(lambda x tau-scale {1,2} x epsilon {0.05,0.2}); order variants CE, feature KD
and gate; current-only teacher with feature KD (lambda). Matched controls use
the proposed gate's chosen setting: shuffled gate (within class x condition),
in-sample student-residual gate, non-grouped (random window folds) bridges,
gate without class normalisation, larger bridge. Bridge + linear head is the
separately reported auxiliary control.

Protocol B (per held-out setting): fixed defaults declared here (lambda 1,
tau = median residual, epsilon 0.2), 40 epochs, last epoch kept; no checkpoint
or hyper-parameter is selected on any data of the held-out setting. Methods:
CE, feature KD, SAAMask re-implementation, proposed gate, and the order
variants CE, feature KD, gate. Seeds 0, 1, 2 vary student initialisation and
data order only; teacher and bridges are trained once per unit with seed 0.

Freeze record: `reports/protocol_freeze.json` (SHA-256 of this file, the split
manifests and the source files at launch).

## Amendment A4 (2026-11-07, while Protocol A was running; before any analysis)

Trigger: the literature synthesis and its adversarial verification
(`reports/novelty_assessment.md`, `reports/verification_of_claims.md`) found
that every ingredient of the mechanism has a precedent and that
vibration-to-current distillation into a current-only student is published
(Xie et al. 2025, full text). Exposure at the time of writing: no analysis had
been run; one console line had displayed a single test score (SAAMask, Protocol
A fold 0, seed 0); no comparison between methods had been seen.

1. Framing: the study is an empirical, bearing-grouped evaluation. Working
   title: "When Does Vibration-Aware Distillation Help Current-Only Bearing
   Fault Diagnosis? A Bearing-Grouped Study on Unseen Bearings and Operating
   Conditions". "Transferability-aware" is dropped; the residual is called a
   proxy for transfer difficulty only if its association with held-out student
   error (diagnostic 5 below) is positive.
2. Primary Holm family (Protocol A, recording-level macro-F1, paired over
   bearings): proposed gate vs CE-only; vs ungated feature KD; vs SAAMask-style
   adaptation; vs shuffled gate; vs in-sample residual gate (five contrasts).
3. H2 counts as supported only if the proposed gate beats **both** the shuffled
   and the in-sample gate with bearing-level intervals that exclude zero.
4. Protocol B adds the in-sample gate and the shuffled gate with the same fixed
   defaults (code change before Protocol B started; re-hashed in
   `reports/protocol_freeze.json`).
5. Added diagnostics (descriptive, never used for any choice): between- versus
   within-bearing share of residual variance; out-of-group R^2 of the teacher
   bottleneck from current per fold and representation; association between a
   test window's bridge residual (bridge refitted on all training bearings, as
   in the auxiliary control) and the student's error on that window.
6. Reporting: method 4 is a "CPFD-style teacher-confidence gate (adapted)";
   method 5 is a "SAAMask-style adaptation" with an adaptation table; the
   tuning-budget asymmetry in Protocol A (gate 8 settings, logit KD 4, feature
   KD 2) is reported, and Protocol B, where every method uses the same fixed
   defaults, serves as the equal-budget comparison. The teacher is not
   cross-fitted, and no double/debiased-ML guarantee is claimed.

## Amendment A5 (2026-11-07, after the adversarial code review; all earlier main runs voided)

The review workflow (`wf_702a2f4e-6dd`; findings verified independently) found
defects that invalidate the stopped main runs (registry entry, attempt 3):

1. **Time base (supersedes D06).** The stored time vectors are faulty: on
   blocks with irregular steps the supply frequency from the sample index stays
   at 99.9-100.2 Hz, whereas the time vector would imply 181-316 Hz (checked on
   KA03_2, K001_2, K002_10). Samples are uniformly spaced at 64 kHz; long files
   are simply longer than 4 s. Caches v2 use the sample index (first 4.0 s);
   decision D12. A regression test checks a constant ~100 Hz fundamental in
   every window of KA03_2.
2. **Distillation scale.** The alignment term is now summed over the 64
   dimensions (about 1 - cos) instead of averaged (which gave lambda(1-cos)/64);
   the masked variant rescales kept dimensions to 64. Lambda grids unchanged.
3. **Order front-end.** Band-limiting uses a mirror extension (no wrap-around
   ringing); the log order spectrum averages two 28-cycle segments (window
   start and last complete cycle), so the whole window is used at every speed.
4. **Decimation.** Kaiser FIR with cut-off at 0.8 x the output Nyquist.
5. **Windows** must be complete in both modalities; `amp` is honoured at
   inference; the teacher bottleneck is no longer stored under the key `fe`.

Pilot decisions re-derived on caches v2 with the unchanged rules
(`results/pilot/`, `results/pilot/diag_representation_choice.json`): current rate
8 kHz (CE 0.306 vs 0.304 at 16 kHz); representation log-magnitude spectrum
(0.429 vs 0.372); epoch budget 40 with patience 10, taken from Pilot-S/A only.
Pilot-B values are descriptive and were not used for any decision. Everything
else in A1-A4 stands.

## 11. KAIST
Decision D09 (final): the paired, bearing-grouped replication is unavailable
(two unsynchronised acquisition systems with no documented shared clock or
trigger; one specimen per class/severity; class confounded with recording day;
class-dependent current-channel availability; a file-name swap in the 0 Nm
inner-race current files). It is reported as a documented feasibility finding.
No window-level or random-split substitute is run.

## Amendment A6 (2026-11-07 20:33, after the pre-registered analysis was run and inspected)

Nothing below changes a model, a setting, a hypothesis or a primary result. Additions are labelled
post hoc and descriptive wherever they are reported.

1. Diagnostic 5 (declared in A4) was implemented in `scripts/diag_residual_error.py` at 20:23, after the
   pre-registered Protocol A results (20:20) had been inspected and before the diagnostic was first run (20:25);
   its residual, reference student, error measure and association statistics are fixed in the script header
   (output `results/analysis/diag5_residual_vs_error.json`). The manuscript says so.
2. Post hoc, descriptive (`scripts/analyze_supplement.py`, `results/analysis/supplement.json`): the
   multimodal teacher against the CE-only student with the same paired bearing bootstrap; the minimum
   detectable effect (80% power) of each primary contrast from its bootstrap standard error; a Holm
   adjustment over the 20 gate contrasts of Protocol B as a sensitivity check of the unadjusted
   intervals; class-wise recall (a secondary endpoint of section 9.1).
3. Deployment (section 10) was extended after the first export: the parity check now also compares the
   deployment preprocessing with the GPU front-end used for training and evaluation, and the exported
   models are compared with the stored evaluation predictions of the same checkpoint at window and
   recording level (`scripts/export_benchmark.py`, `results/deploy/benchmark_<checkpoint>.json`). The order
   variant (`A_fold0_ce_ord_s0`) is exported as well, because H3 concerns it. The first export report,
   which compared only with PyTorch CPU preprocessing, is kept in `results/deploy/_superseded/`.
