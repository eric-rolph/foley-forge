"""Loudness normalization + auto-ducking command builders (ffmpeg).

The highest-synergy roadmap feature: after foley-forge places SFX, normalize the
mix to a YouTube-friendly target (EBU R128, ~-14 LUFS integrated, -1 dBTP) using a
two-pass ``loudnorm`` (so dynamics survive), and duck SFX/music under the speech
track with ``sidechaincompress`` — the OSS equivalent of Resolve's IntelliTrack.

These builders are pure (return ffmpeg argument lists) so they're unit-testable;
a thin :func:`run_loudnorm` executes them when ffmpeg is available.
"""

from __future__ import annotations

import json
import shutil
import subprocess

TARGET_I = -14.0    # integrated loudness (LUFS), YouTube-ish
TARGET_TP = -1.0    # true peak (dBTP)
TARGET_LRA = 11.0   # loudness range


def build_loudnorm_measure_cmd(input_path: str, ffmpeg: str = "ffmpeg") -> list[str]:
    """Pass 1: measure loudness, printing JSON stats to stderr."""
    return [
        ffmpeg, "-hide_banner", "-i", input_path,
        "-af",
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}:print_format=json",
        "-f", "null", "-",
    ]


def build_loudnorm_apply_cmd(
    input_path: str, output_path: str, measured: dict, ffmpeg: str = "ffmpeg"
) -> list[str]:
    """Pass 2: apply linear normalization using the measured values from pass 1."""
    af = (
        f"loudnorm=I={TARGET_I}:TP={TARGET_TP}:LRA={TARGET_LRA}"
        f":measured_I={measured.get('input_i', 0)}"
        f":measured_TP={measured.get('input_tp', 0)}"
        f":measured_LRA={measured.get('input_lra', 0)}"
        f":measured_thresh={measured.get('input_thresh', 0)}"
        f":offset={measured.get('target_offset', 0)}:linear=true"
    )
    return [ffmpeg, "-y", "-i", input_path, "-af", af, output_path]


def build_duck_cmd(
    music_path: str,
    voice_path: str,
    output_path: str,
    threshold: float = 0.03,
    ratio: float = 8.0,
    attack: float = 20.0,
    release: float = 300.0,
    ffmpeg: str = "ffmpeg",
) -> list[str]:
    """Duck ``music_path`` under ``voice_path`` (voice as sidechain trigger)."""
    fc = (
        f"[0:a][1:a]sidechaincompress="
        f"threshold={threshold}:ratio={ratio}:attack={attack}:release={release}[out]"
    )
    return [
        ffmpeg, "-y", "-i", music_path, "-i", voice_path,
        "-filter_complex", fc, "-map", "[out]", output_path,
    ]


def run_loudnorm(input_path: str, output_path: str) -> bool:
    """Execute the two-pass normalization. Returns True on success."""
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        return False
    p1 = subprocess.run(
        build_loudnorm_measure_cmd(input_path, ffmpeg),
        capture_output=True, text=True)
    measured = _parse_loudnorm_json(p1.stderr)
    if not measured:
        return False
    p2 = subprocess.run(
        build_loudnorm_apply_cmd(input_path, output_path, measured, ffmpeg),
        capture_output=True, text=True)
    return p2.returncode == 0


def _parse_loudnorm_json(stderr: str) -> dict:
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(stderr[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}
