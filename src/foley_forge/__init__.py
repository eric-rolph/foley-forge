"""foley-forge — auto-foley for video editors.

Detect on-screen physical interactions with a pluggable VLM backend, match them to
sound effects, and export an editor timeline (FCPXML / FCP7 XML / EDL).
"""

from __future__ import annotations

__version__ = "0.1.0"

from .config import Config
from .models import AnalysisResult, Cue, Timeline, TimelineClip

__all__ = ["__version__", "Config", "AnalysisResult", "Cue", "Timeline", "TimelineClip"]


def run(video_path: str, config: Config | None = None, outdir: str = "out") -> dict:
    """Convenience API: run the full pipeline with defaults. See :mod:`foley_forge.pipeline`."""
    from .pipeline import run as _run
    return _run(video_path, config or Config(), outdir)
