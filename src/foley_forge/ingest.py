"""Video ingest: probe metadata and extract audio via ffmpeg/ffprobe.

OpenCV is great at decoding frames but unreliable for container metadata and audio,
so foley-forge shells out to ffprobe/ffmpeg (which handle the widest range of
containers and codecs). ffmpeg must be on PATH.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from .timecode import normalize_fps


class FFmpegNotFound(RuntimeError):
    pass


@dataclass
class VideoInfo:
    path: str
    fps: float
    duration: float
    width: int
    height: int
    has_audio: bool
    vcodec: str = ""


def _tool(name: str) -> str:
    exe = shutil.which(name)
    if not exe:
        raise FFmpegNotFound(
            f"{name} not found on PATH. Install ffmpeg (https://ffmpeg.org) and retry.")
    return exe


def probe(path: str) -> VideoInfo:
    """Probe a video for fps, duration, resolution, and audio presence."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(path)
    ffprobe = _tool("ffprobe")
    cmd = [
        ffprobe, "-v", "error", "-print_format", "json",
        "-show_format", "-show_streams", str(p),
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, check=True)
    data = json.loads(out.stdout)

    vstream = next((s for s in data.get("streams", []) if s.get("codec_type") == "video"), None)
    if vstream is None:
        raise ValueError(f"no video stream in {path}")
    has_audio = any(s.get("codec_type") == "audio" for s in data.get("streams", []))

    fps = normalize_fps(vstream.get("avg_frame_rate") or vstream.get("r_frame_rate") or "30")
    if fps <= 0:
        fps = normalize_fps(vstream.get("r_frame_rate") or "30") or 30.0

    duration = 0.0
    for src in (data.get("format", {}).get("duration"), vstream.get("duration")):
        try:
            duration = float(src)
            if duration > 0:
                break
        except (TypeError, ValueError):
            continue

    return VideoInfo(
        path=str(p),
        fps=fps,
        duration=duration,
        width=int(vstream.get("width", 0)),
        height=int(vstream.get("height", 0)),
        has_audio=has_audio,
        vcodec=vstream.get("codec_name", ""),
    )


def extract_audio(path: str, out_wav: str, sample_rate: int = 16000) -> str | None:
    """Extract a mono PCM WAV for onset analysis. Returns None if there's no audio."""
    ffmpeg = _tool("ffmpeg")
    out = Path(out_wav)
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg, "-y", "-i", str(path),
        "-vn", "-ac", "1", "-ar", str(sample_rate),
        "-acodec", "pcm_s16le", str(out),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        return None
    return str(out)
