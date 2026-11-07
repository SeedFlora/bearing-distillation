"""Electrical-order front-end for current windows (current-only, tachometer-free).

The drive is a permanent-magnet synchronous motor with p = 4 pole pairs, so the
supply (electrical) frequency equals p times the shaft frequency exactly, and
bearing defect frequencies, which scale with the shaft frequency, sit at fixed
*electrical orders*. The front-end estimates the supply frequency from the
window itself (Hann-windowed FFT peak in 20-200 Hz with parabolic
interpolation), band-limits the window to ``max_order`` x f_e and resamples it
onto a grid of ``samples_per_cycle`` points per electrical cycle for a fixed
number of cycles. No metadata, speed channel or other window is used.
"""
from __future__ import annotations

import math

import torch
import torch.nn as nn


class ElectricalOrderFrontEnd(nn.Module):
    stem_stride = 4

    def __init__(self, fs: int, window: int, cycles: int = 28, samples_per_cycle: int = 64, max_order: int = 32,
                 f_lo: float = 20.0, f_hi: float = 200.0, nfft: int = 32768, upsample: int = 4):
        super().__init__()
        self.fs, self.window, self.cycles, self.spc = fs, window, cycles, samples_per_cycle
        self.max_order, self.nfft, self.upsample = max_order, nfft, upsample
        self.k_lo = int(math.ceil(f_lo * nfft / fs))
        self.k_hi = int(math.floor(f_hi * nfft / fs))
        self.register_buffer("hann", torch.hann_window(window, periodic=False), persistent=False)
        self.out_len = cycles * samples_per_cycle

    @torch.no_grad()
    def estimate_fe(self, x: torch.Tensor) -> torch.Tensor:
        w = (x - x.mean(-1, keepdim=True)) * self.hann
        mag = torch.fft.rfft(w, n=self.nfft).abs()
        k = mag[:, self.k_lo:self.k_hi].argmax(-1) + self.k_lo
        lm = torch.log(mag + 1e-12)
        a = lm.gather(1, (k - 1)[:, None]).squeeze(1)
        b = lm.gather(1, k[:, None]).squeeze(1)
        c = lm.gather(1, (k + 1)[:, None]).squeeze(1)
        den = a - 2 * b + c
        delta = torch.where(den.abs() > 1e-12, 0.5 * (a - c) / den, torch.zeros_like(den)).clamp(-0.5, 0.5)
        return (k.to(x.dtype) + delta) * self.fs / self.nfft

    @torch.no_grad()
    def band_limited_upsampled(self, x: torch.Tensor, fe: torch.Tensor) -> torch.Tensor:
        """Band-limit to max_order x f_e on a mirror (even) extension, which removes the wrap-around
        ringing of a periodic FFT filter, and upsample by ``upsample``; returns (B, W*upsample)."""
        b, w = x.shape
        xm = torch.cat([x, x.flip(-1)], dim=-1)
        X = torch.fft.rfft(xm, n=2 * w)
        freqs = torch.arange(X.shape[-1], device=x.device, dtype=x.dtype) * self.fs / (2 * w)
        X = X * (freqs[None, :] <= (self.max_order * fe)[:, None])
        n_up = w * self.upsample
        return (torch.fft.irfft(X, n=2 * n_up) * self.upsample)[:, :n_up]

    @torch.no_grad()
    def resample(self, xu: torch.Tensor, fe: torch.Tensor, offset_cycles: torch.Tensor | None = None) -> torch.Tensor:
        n_up = xu.shape[1]
        k = torch.arange(self.out_len, device=xu.device, dtype=xu.dtype)[None, :]
        if offset_cycles is not None:
            k = k + offset_cycles[:, None].to(xu.dtype) * self.spc
        pos = (k / (self.spc * fe[:, None]) * (self.fs * self.upsample)).clamp(0, n_up - 1.001)
        i0 = pos.floor().long()
        frac = pos - i0
        return xu.gather(1, i0) * (1 - frac) + xu.gather(1, i0 + 1) * frac

    @torch.no_grad()
    def forward(self, x: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        """x: (B, W) float32 raw current window -> ((B, cycles*spc) from the window start, f_e (B,))."""
        x = x.float()
        if x.shape[1] != self.window:
            raise ValueError(f"expected windows of {self.window} samples, got {x.shape[1]}")
        fe = self.estimate_fe(x)
        return self.resample(self.band_limited_upsampled(x, fe), fe), fe


def _log_magnitude(x: torch.Tensor, window: torch.Tensor, n_keep: int, floor_db: float = 140.0) -> torch.Tensor:
    mag = torch.fft.rfft((x - x.mean(-1, keepdim=True)) * window).abs()[:, :n_keep]
    floor = mag.amax(-1, keepdim=True) * (10 ** (-floor_db / 20))
    return 20 * torch.log10(mag + floor)


class LogSpectrumFrontEnd(nn.Module):
    """Fixed per-window transform: Hann-windowed log-magnitude spectrum up to ``f_max`` (Hz axis).

    The logarithm compresses the ~70-dB gap between the supply fundamental and
    the weak components that carry bearing information.
    """

    stem_stride = 2

    def __init__(self, fs: int, window: int, f_max: float = 4000.0):
        super().__init__()
        self.n_keep = int(f_max * window / fs) + 1
        self.register_buffer("hann", torch.hann_window(window, periodic=False), persistent=False)

    @torch.no_grad()
    def forward(self, x: torch.Tensor):
        return _log_magnitude(x.float(), self.hann, self.n_keep), None


class LogOrderSpectrumFrontEnd(nn.Module):
    """Electrical-order resampling followed by a log-magnitude *order* spectrum (orders 0..max_order).

    With 28 cycles per window the order resolution is 1/28; the fundamental and
    its harmonics fall on exact bins whatever the speed.
    """

    stem_stride = 2

    def __init__(self, fs: int, window: int, cycles: int = 28, samples_per_cycle: int = 64, max_order: int = 32):
        super().__init__()
        self.order = ElectricalOrderFrontEnd(fs, window, cycles=cycles, samples_per_cycle=samples_per_cycle,
                                             max_order=max_order)
        n = cycles * samples_per_cycle
        self.n_keep = max_order * cycles + 1
        self.register_buffer("hann", torch.hann_window(n, periodic=False), persistent=False)

    @torch.no_grad()
    def forward(self, x: torch.Tensor):
        """Two 28-cycle segments, at the window start and ending at the last complete cycle, so the
        whole window is used at every speed; their Hann magnitude spectra are averaged before the log."""
        x = x.float()
        o = self.order
        fe = o.estimate_fe(x)
        xu = o.band_limited_upsampled(x, fe)
        n_avail = torch.floor(x.shape[1] * fe / o.fs)
        last = (n_avail - o.cycles).clamp_min(0)
        mags = []
        for off in (torch.zeros_like(fe), last):
            y = o.resample(xu, fe, off)
            mags.append(torch.fft.rfft((y - y.mean(-1, keepdim=True)) * self.hann).abs()[:, :self.n_keep])
        mag = 0.5 * (mags[0] + mags[1])
        floor = mag.amax(-1, keepdim=True) * (10 ** (-140.0 / 20))
        return 20 * torch.log10(mag + floor), fe
