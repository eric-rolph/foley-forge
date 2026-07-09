"""Shared pytest fixtures, including a synthesized test video (needs ffmpeg)."""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from foley_forge.models import Timeline, TimelineClip

HAS_FFMPEG = shutil.which("ffmpeg") is not None
requires_ffmpeg = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg not on PATH")


def _write_click_wav(path: Path, clicks=(0.5, 1.0, 1.5, 2.0, 2.5), sr=44100, dur=3.0) -> None:
    import wave

    import numpy as np
    n = int(dur * sr)
    y = np.zeros(n, dtype=np.float32)
    t = np.arange(n) / sr
    for c in clicks:
        s = int(c * sr)
        seg = np.exp(-(np.arange(n - s)) / (0.01 * sr)) * np.sin(2 * np.pi * 900 * t[: n - s])
        y[s:] += seg.astype(np.float32)
    data = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


@pytest.fixture(scope="session")
def sample_video(tmp_path_factory) -> Path:
    """A 3s 320x240 clip with motion and periodic audio clicks (for onset detection)."""
    if not HAS_FFMPEG:
        pytest.skip("ffmpeg not on PATH")
    media = tmp_path_factory.mktemp("media")
    wav = media / "clicks.wav"
    _write_click_wav(wav)
    out = media / "sample.mp4"
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc2=size=320x240:rate=30:duration=3",
        "-i", str(wav),
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest",
        str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists():
        pytest.skip(f"could not synthesize test video: {proc.stderr[-400:]}")
    return out


@pytest.fixture
def simple_timeline(tmp_path) -> Timeline:
    """A timeline with a source video and three overlapping-ish SFX clips."""
    wav = tmp_path / "whoosh.wav"
    wav.write_bytes(b"RIFF0000WAVEfmt ")  # placeholder; exporters only need the path
    tl = Timeline(fps=30.0, name="test", width=1920, height=1080)
    tl.add(TimelineClip(name="src.mp4", media_path=str(tmp_path / "src.mp4"),
                        start=0.0, duration=10.0, kind="video"))
    tl.add(TimelineClip(name="whoosh", media_path=str(wav), start=1.0, duration=0.5))
    tl.add(TimelineClip(name="impact", media_path=str(wav), start=1.2, duration=0.5))  # overlaps
    tl.add(TimelineClip(name="ding", media_path=str(wav), start=5.0, duration=0.6))
    return tl
