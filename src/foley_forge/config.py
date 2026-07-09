"""Configuration: dataclass defaults merged from an optional TOML file + CLI flags."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import tomllib


@dataclass
class Config:
    # sampling
    sample_fps: float = 1.5
    max_frames: int = 400
    include_cuts: bool = True
    # scenes
    scene_threshold: float = 27.0
    # backend
    backend: str = "mock"
    backend_config: dict = field(default_factory=dict)
    # fusion
    snap_window: float = 0.35
    min_gap: float = 0.20
    min_confidence: float = 0.35
    # match
    use_clap: bool = False
    min_score: float = 0.20
    gain_db: float = -6.0
    commercial: bool = True
    # export
    formats: list[str] = field(default_factory=lambda: ["fcp7xml", "fcpxml", "edl"])
    include_source_video: bool = True
    audio_role: str = "effects"
    # sfx
    sfx_libraries: list[str] = field(default_factory=list)

    @classmethod
    def load(cls, path: str | Path | None = None) -> Config:
        cfg = cls()
        if not path:
            return cfg
        data = tomllib.loads(Path(path).read_text(encoding="utf-8"))

        s = data.get("sampling", {})
        cfg.sample_fps = float(s.get("fps", cfg.sample_fps))
        cfg.max_frames = int(s.get("max_frames", cfg.max_frames))
        cfg.include_cuts = bool(s.get("include_cuts", cfg.include_cuts))

        sc = data.get("scenes", {})
        cfg.scene_threshold = float(sc.get("threshold", cfg.scene_threshold))

        b = data.get("backend", {})
        cfg.backend = str(b.get("name", cfg.backend))
        cfg.backend_config = {k: v for k, v in b.items() if k != "name"}

        f = data.get("fusion", {})
        cfg.snap_window = float(f.get("snap_window", cfg.snap_window))
        cfg.min_gap = float(f.get("min_gap", cfg.min_gap))
        cfg.min_confidence = float(f.get("min_confidence", cfg.min_confidence))

        m = data.get("match", {})
        cfg.use_clap = bool(m.get("use_clap", cfg.use_clap))
        cfg.min_score = float(m.get("min_score", cfg.min_score))
        cfg.gain_db = float(m.get("gain_db", cfg.gain_db))
        cfg.commercial = bool(m.get("commercial", cfg.commercial))

        e = data.get("export", {})
        cfg.formats = list(e.get("formats", cfg.formats))
        cfg.include_source_video = bool(e.get("include_source_video", cfg.include_source_video))
        cfg.audio_role = str(e.get("audio_role", cfg.audio_role))

        sfx = data.get("sfx", {})
        cfg.sfx_libraries = list(sfx.get("libraries", cfg.sfx_libraries))
        return cfg
