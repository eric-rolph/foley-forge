"""Onset detection.

The caption backend tells us *what* interaction happens near a frame; the audio
onset tells us *when* the impact actually lands (to a few milliseconds). Snapping
each detected interaction to the nearest onset is what makes an auto-placed SFX feel
hand-synced. Prefers librosa; falls back to a dependency-free numpy spectral-flux
detector so the tool works with only numpy installed.
"""

from __future__ import annotations

import wave

import numpy as np


def read_wav_mono(path: str) -> tuple[np.ndarray, int]:
    """Read a PCM WAV into a float32 mono signal in [-1, 1] plus its sample rate."""
    with wave.open(str(path), "rb") as w:
        sr = w.getframerate()
        n = w.getnframes()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(n)

    if sw == 1:
        y = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    elif sw == 2:
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        y = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    else:  # pragma: no cover - unusual sample widths
        y = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0

    if ch > 1:
        y = y.reshape(-1, ch).mean(axis=1)
    return y, sr


def detect_onsets(wav_path: str, min_separation: float = 0.05) -> list[float]:
    """Return onset times (seconds). Uses librosa if available, else numpy fallback."""
    try:
        import librosa
        y, sr = librosa.load(str(wav_path), sr=None, mono=True)
        times = librosa.onset.onset_detect(
            y=y, sr=sr, units="time", backtrack=True)
        return _dedupe(list(map(float, times)), min_separation)
    except ImportError:
        y, sr = read_wav_mono(wav_path)
        return _dedupe(_onsets_numpy(y, sr), min_separation)


def _dedupe(times: list[float], min_sep: float) -> list[float]:
    times = sorted(times)
    out: list[float] = []
    for t in times:
        if not out or t - out[-1] >= min_sep:
            out.append(t)
    return out


def _onsets_numpy(
    y: np.ndarray, sr: int, hop: int = 512, win: int = 1024, delta: float = 0.12
) -> list[float]:
    """Spectral-flux onset detector with an adaptive local threshold."""
    if len(y) < win or sr <= 0:
        return []
    window = np.hanning(win).astype(np.float32)
    n_frames = 1 + (len(y) - win) // hop
    flux = np.zeros(n_frames, dtype=np.float32)
    prev = None
    for i in range(n_frames):
        seg = y[i * hop:i * hop + win] * window
        mag = np.abs(np.fft.rfft(seg))
        if prev is not None:
            d = mag - prev
            flux[i] = float(np.sum(d[d > 0]))
        prev = mag

    peak = flux.max()
    if peak <= 0:
        return []
    flux /= peak

    times: list[float] = []
    w = 5
    for i in range(n_frames):
        lo, hi = max(0, i - w), min(n_frames, i + w + 1)
        local = flux[lo:hi]
        if flux[i] >= local.mean() + delta and flux[i] >= local.max() - 1e-6 and flux[i] > 0.2:
            times.append(i * hop / sr)
    return times
