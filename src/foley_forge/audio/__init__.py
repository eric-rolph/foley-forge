"""Audio analysis: onset detection (the precise 'when' for each cue)."""

from .onsets import detect_onsets, read_wav_mono

__all__ = ["detect_onsets", "read_wav_mono"]
