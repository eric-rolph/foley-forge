"""Shared data models passed between pipeline stages.

These are deliberately plain dataclasses (JSON-serializable via :func:`to_dict`)
so the scene narrative and any future GUI can round-trip them without importing
heavy dependencies.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path


@dataclass
class Frame:
    """A single sampled frame handed to a caption backend."""

    index: int
    t: float                       # seconds into the video
    image: object = None           # np.ndarray (BGR) or None; not serialized
    is_cut: bool = False           # sampled because a scene cut was detected here


@dataclass
class Interaction:
    """A physical interaction the backend reports in one frame."""

    label: str                     # canonical taxonomy key (e.g. "door_slam") or raw text
    confidence: float = 0.5
    subject: str = ""              # optional actor ("person")
    obj: str = ""                  # optional object ("door")
    raw: str = ""                  # backend's original phrase, for debugging

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SceneObservation:
    """A backend's read of one sampled frame."""

    t: float
    description: str
    interactions: list[Interaction] = field(default_factory=list)
    source: str = ""               # backend name

    def to_dict(self) -> dict:
        d = asdict(self)
        return d


@dataclass
class SFXMatch:
    """The sound chosen for a cue."""

    asset_id: str
    name: str
    path: str
    license: str = "CC0-1.0"
    attribution: str = ""          # empty for CC0; "Author (source, url)" for CC-BY
    score: float = 0.0
    match_type: str = "lexical"    # lexical | clap | fallback
    duration: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class Cue:
    """A placed sound-effect event on the timeline."""

    t: float                       # precise onset-snapped time, seconds
    event: str                     # canonical event label
    confidence: float
    source: str                    # "vlm+onset", "vlm", "cut", "onset"
    description: str = ""
    sfx: SFXMatch | None = None
    gain_db: float = -6.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["sfx"] = self.sfx.to_dict() if self.sfx else None
        return d


@dataclass
class TimelineClip:
    """One clip placed on the exported timeline."""

    name: str
    media_path: str
    start: float                   # timeline position, seconds
    duration: float                # seconds
    kind: str = "audio"            # "audio" | "video"
    gain_db: float = 0.0
    lane: int = -1                 # FCPXML lane (negative = below primary)
    role: str = "effects"          # FCPXML audioRole
    channels: int = 1

    @property
    def end(self) -> float:
        return self.start + self.duration


@dataclass
class Timeline:
    """The editor timeline foley-forge exports."""

    fps: float
    name: str = "foley-forge"
    width: int = 1920
    height: int = 1080
    duration: float = 0.0          # total sequence length, seconds
    clips: list[TimelineClip] = field(default_factory=list)

    def add(self, clip: TimelineClip) -> None:
        self.clips.append(clip)
        self.duration = max(self.duration, clip.end)

    @property
    def audio_clips(self) -> list[TimelineClip]:
        return [c for c in self.clips if c.kind == "audio"]

    @property
    def video_clips(self) -> list[TimelineClip]:
        return [c for c in self.clips if c.kind == "video"]


@dataclass
class AnalysisResult:
    """Everything a run produced; drives narrative + exports."""

    video_path: str
    fps: float
    duration: float
    width: int
    height: int
    backend: str
    observations: list[SceneObservation] = field(default_factory=list)
    onsets: list[float] = field(default_factory=list)
    cues: list[Cue] = field(default_factory=list)
    timeline: Timeline | None = None

    def to_dict(self) -> dict:
        return {
            "video_path": self.video_path,
            "fps": self.fps,
            "duration": self.duration,
            "resolution": [self.width, self.height],
            "backend": self.backend,
            "observations": [o.to_dict() for o in self.observations],
            "onsets": self.onsets,
            "cues": [c.to_dict() for c in self.cues],
        }


def media_uri_stem(path: str | Path) -> str:
    """Absolute POSIX-ish path used to build ``file://`` URIs for media."""
    return Path(path).resolve().as_posix()
