"""Roadmap 'automated editing' helpers that complement the SFX core.

v0.1 ships real, testable building blocks; the CLI wiring for a full render pass
lands in v0.2 (see ROADMAP.md).
"""

from .beats import detect_beats
from .loudness import build_duck_cmd, build_loudnorm_apply_cmd, build_loudnorm_measure_cmd

__all__ = [
    "detect_beats",
    "build_loudnorm_measure_cmd",
    "build_loudnorm_apply_cmd",
    "build_duck_cmd",
]
