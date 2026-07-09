"""CMX3600 EDL exporter — the lossy, universal fallback.

An EDL carries audio-only events but has hard limits: max 999 events, ~4 audio
channels, frame-accurate (not sample-accurate), and **no real media path** — the
filename survives only in a ``* FROM CLIP NAME:`` comment used to relink on import.
Offer it for maximum-compatibility conform workflows; prefer xmeml/FCPXML otherwise.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Timeline
from ..timecode import edl_rate, edl_timecode
from .base import Exporter

MAX_EVENTS = 999


class EDLExporter(Exporter):
    ext = ".edl"

    def __init__(self, channel: str = "AA", title: str = "foley-forge"):
        self.channel = channel
        self.title = title
        self.truncated = 0

    def export(self, timeline: Timeline) -> str:
        fps = timeline.fps
        _, drop = edl_rate(fps)
        lines: list[str] = [
            f"TITLE: {self.title}",
            f"FCM: {'DROP FRAME' if drop else 'NON-DROP FRAME'}",
        ]

        clips = sorted(timeline.audio_clips, key=lambda c: (c.start, c.end))
        self.truncated = max(0, len(clips) - MAX_EVENTS)
        for i, clip in enumerate(clips[:MAX_EVENTS], start=1):
            src_in = edl_timecode(0.0, fps)
            src_out = edl_timecode(clip.duration, fps)
            rec_in = edl_timecode(clip.start, fps)
            rec_out = edl_timecode(clip.end, fps)
            lines.append(
                f"{i:03d}  {'AX':<8} {self.channel:<4} {'C':<4} "
                f"{src_in} {src_out} {rec_in} {rec_out}"
            )
            lines.append(f"* FROM CLIP NAME: {Path(clip.media_path).name}")

        if self.truncated:
            lines.append(f"* NOTE: {self.truncated} event(s) dropped (CMX3600 999-event limit)")
        return "\n".join(lines) + "\n"


def export_edl(timeline: Timeline, channel: str = "AA", title: str = "foley-forge") -> str:
    return EDLExporter(channel, title).export(timeline)
