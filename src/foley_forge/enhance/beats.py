"""Beat detection for snapping SFX/cuts to musical beats (librosa)."""

from __future__ import annotations


def detect_beats(wav_path: str) -> list[float]:
    """Return beat times (seconds), or [] if librosa isn't installed."""
    try:
        import librosa
    except ImportError:
        return []
    y, sr = librosa.load(str(wav_path), sr=None, mono=True)
    _tempo, beats = librosa.beat.beat_track(y=y, sr=sr, units="time")
    return [float(b) for b in beats]


def snap_to_beats(times: list[float], beats: list[float], window: float = 0.12) -> list[float]:
    """Snap each time to the nearest beat within ``window`` seconds."""
    if not beats:
        return times
    out = []
    for t in times:
        nearest = min(beats, key=lambda b: abs(b - t))
        out.append(nearest if abs(nearest - t) <= window else t)
    return out
