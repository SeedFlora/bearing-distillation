"""Network definitions.

Temporal resolution after each stem is fixed at 1 ms (stem stride = fs/1000),
so the same block stack serves 8-kHz or 16-kHz current and 32-kHz vibration.

* Teacher: one 1D residual branch per modality, concatenated pooled features,
  fusion MLP, linear task bottleneck z (d=64) and a linear classifier on z.
* Student: depthwise-separable 1D CNN on current only, linear classifier, and
  a training-only linear projection to the teacher bottleneck dimension.
* Bridge: current-only residual 1D CNN regressing the L2-normalised teacher
  bottleneck (output is normalised too).
"""
from __future__ import annotations

import torch
import torch.nn as nn
import torch.nn.functional as F


def count_parameters(m: nn.Module, trainable_only: bool = False) -> int:
    return sum(p.numel() for p in m.parameters() if (p.requires_grad or not trainable_only))


class Stem(nn.Module):
    def __init__(self, fs: int | None, out_ch: int, stride: int | None = None):
        super().__init__()
        stride = int(stride) if stride else int(fs // 1000)
        k = 8 * stride
        self.conv = nn.Conv1d(1, out_ch, kernel_size=k, stride=stride, padding=k // 2 - stride // 2, bias=False)
        self.bn = nn.BatchNorm1d(out_ch)

    def forward(self, x):
        return F.relu(self.bn(self.conv(x)))


class ResBlock(nn.Module):
    def __init__(self, cin: int, cout: int, stride: int):
        super().__init__()
        self.c1 = nn.Conv1d(cin, cout, 7, stride=stride, padding=3, bias=False)
        self.b1 = nn.BatchNorm1d(cout)
        self.c2 = nn.Conv1d(cout, cout, 7, padding=3, bias=False)
        self.b2 = nn.BatchNorm1d(cout)
        self.skip = None
        if stride != 1 or cin != cout:
            self.skip = nn.Sequential(nn.Conv1d(cin, cout, 1, stride=stride, bias=False), nn.BatchNorm1d(cout))

    def forward(self, x):
        y = F.relu(self.b1(self.c1(x)))
        y = self.b2(self.c2(y))
        return F.relu(y + (x if self.skip is None else self.skip(x)))


class ResBranch(nn.Module):
    """Residual 1D CNN branch ending in global average pooling."""

    def __init__(self, fs: int | None, widths=(32, 64, 128), stem_stride: int | None = None):
        super().__init__()
        self.stem = Stem(fs, widths[0], stride=stem_stride)
        blocks, cin = [], widths[0]
        for w in widths:
            blocks.append(ResBlock(cin, w, stride=2))
            cin = w
        self.blocks = nn.Sequential(*blocks)
        self.out_dim = widths[-1]

    def forward(self, x):
        return self.blocks(self.stem(x)).mean(dim=-1)


class Teacher(nn.Module):
    def __init__(self, fs_current: int, fs_vibration: int | None, n_classes: int = 3, bottleneck: int = 64,
                 widths=(32, 64, 128), dropout: float = 0.2):
        super().__init__()
        self.current = ResBranch(fs_current, widths)
        self.vibration = ResBranch(fs_vibration, widths) if fs_vibration else None  # None -> current-only control
        fused = self.current.out_dim + (self.vibration.out_dim if self.vibration is not None else 0)
        self.fusion = nn.Sequential(nn.Linear(fused, 128), nn.ReLU(), nn.Dropout(dropout))
        self.bottleneck = nn.Linear(128, bottleneck)
        self.classifier = nn.Linear(bottleneck, n_classes)

    def forward(self, x_current, x_vibration=None):
        h = [self.current(x_current)]
        if self.vibration is not None:
            if x_vibration is None:
                raise ValueError("multimodal teacher needs the paired vibration window")
            h.append(self.vibration(x_vibration))
        z = self.bottleneck(self.fusion(torch.cat(h, dim=1)))
        return self.classifier(z), z


class DSBlock(nn.Module):
    def __init__(self, cin: int, cout: int, stride: int, k: int = 9):
        super().__init__()
        self.dw = nn.Conv1d(cin, cin, k, stride=stride, padding=k // 2, groups=cin, bias=False)
        self.b1 = nn.BatchNorm1d(cin)
        self.pw = nn.Conv1d(cin, cout, 1, bias=False)
        self.b2 = nn.BatchNorm1d(cout)

    def forward(self, x):
        return F.relu(self.b2(self.pw(F.relu(self.b1(self.dw(x))))))


class Student(nn.Module):
    """Deployable current-only model. ``forward`` returns (logits, feature)."""

    def __init__(self, fs_current: int | None, n_classes: int = 3, widths=(16, 32, 48, 64, 96), proj_dim: int | None = 64,
                 stem_stride: int | None = None):
        super().__init__()
        self.stem = Stem(fs_current, widths[0], stride=stem_stride)
        blocks, cin = [], widths[0]
        for w in widths[1:]:
            blocks.append(DSBlock(cin, w, stride=2))
            cin = w
        self.blocks = nn.Sequential(*blocks)
        self.feat_dim = widths[-1]
        self.classifier = nn.Linear(self.feat_dim, n_classes)
        # training-only projection to the teacher bottleneck; dropped at export
        self.proj = nn.Linear(self.feat_dim, proj_dim) if proj_dim else None

    def features(self, x_current):
        return self.blocks(self.stem(x_current)).mean(dim=-1)

    def forward(self, x_current):
        f = self.features(x_current)
        return self.classifier(f), f


class Bridge(nn.Module):
    """Current-only regressor of the normalised teacher bottleneck."""

    def __init__(self, fs_current: int | None, out_dim: int = 64, widths=(16, 32, 64), stem_stride: int | None = None):
        super().__init__()
        self.body = ResBranch(fs_current, widths, stem_stride=stem_stride)
        self.head = nn.Linear(self.body.out_dim, out_dim)

    def forward(self, x_current):
        return F.normalize(self.head(self.body(x_current)), dim=-1)

    def features(self, x_current):
        return self.body(x_current)
