"""CMX3600 EDL exporter — the lossy, universal fallback.

An EDL carries audio-only events but has hard limits: max 999 events, ~4 audio
channels, frame-accurate (not sample-accurate), and **no real media path** — the
filename survives only in a ``* FROM CLIP NAME:`` comment used to relink on import.
Offer it for maximum-compatibility conform workflows; prefer xmeml/FCPXML otherwise.

Overlapping SFX are spread across the four audio channels (A/A2/A3/A4) via the same
lane allocation the XML exporters use, so simultaneous foley doesn't collide on one
track. If more than four overlap at once, the excess share A4 and a NOTE is emitted.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Timeline
from ..timecode import edl_rate, edl_timecode
from .base import Exporter, allocate_lanes

MAX_EVENTS = 999
EDL_CHANNELS = ["A", "A2", "A3", "A4"]


class EDLExporter(Exporter):
    ext = ".edl"

    def __init__(self, channels: list[str] | None = None, title: str = "foley-forge"):
        self.channels = channels or EDL_CHANNELS
        self.title = title
        self.truncated = 0
        self.overflow = 0

    def export(self, timeline: Timeline) -> str:
        fps = timeline.fps
        _, drop = edl_rate(fps)
        lines: list[str] = [
            f"TITLE: {self.title}",
            f"FCM: {'DROP FRAME' if drop else 'NON-DROP FRAME'}",
        ]

        clips = sorted(timeline.audio_clips, key=lambda c: (c.start, c.end))
        self.truncated = max(0, len(clips) - MAX_EVENTS)
        self.overflow = 0
        lane_by_id = {id(c): ln for ln, c in allocate_lanes(clips)}

        for i, clip in enumerate(clips[:MAX_EVENTS], start=1):
            lane = lane_by_id.get(id(clip), 1)
            if lane <= len(self.channels):
                chan = self.channels[lane - 1]
            else:
                chan = self.channels[-1]
                self.overflow += 1
            src_in = edl_timecode(0.0, fps)
            src_out = edl_timecode(clip.duration, fps)
            rec_in = edl_timecode(clip.start, fps)
            rec_out = edl_timecode(clip.end, fps)
            lines.append(
                f"{i:03d}  {'AX':<8} {chan:<4} {'C':<4} "
                f"{src_in} {src_out} {rec_in} {rec_out}"
            )
            lines.append(f"* FROM CLIP NAME: {Path(clip.media_path).name}")

        if self.overflow:
            lines.append(
                f"* NOTE: {self.overflow} overlapping event(s) exceeded "
                f"{len(self.channels)} audio channels and share channel {self.channels[-1]}"
            )
        if self.truncated:
            lines.append(f"* NOTE: {self.truncated} event(s) dropped (CMX3600 999-event limit)")
        return "\n".join(lines) + "\n"


def export_edl(timeline: Timeline, title: str = "foley-forge") -> str:
    return EDLExporter(title=title).export(timeline)
