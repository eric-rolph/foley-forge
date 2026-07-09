"""Shared helpers for timeline exporters."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from abc import ABC, abstractmethod
from pathlib import Path
from urllib.parse import quote

from ..models import Timeline, TimelineClip


def _quoted_abs(path: str) -> str:
    """Absolute, URL-encoded, forward-slash path with a leading slash.

    Windows ``C:\\a b\\x.wav`` -> ``/C:/a%20b/x.wav``; POSIX ``/home/x.wav`` -> ``/home/x.wav``.
    """
    posix = Path(path).resolve().as_posix()
    q = quote(posix, safe="/:")
    if not q.startswith("/"):
        q = "/" + q
    return q


def xmeml_pathurl(path: str) -> str:
    """FCP7 XML ``<pathurl>`` form: ``file://localhost/C:/...``."""
    return "file://localhost" + _quoted_abs(path)


def fcpxml_src(path: str) -> str:
    """FCPXML ``media-rep src`` form: ``file:///C:/...``."""
    return "file://" + _quoted_abs(path)


def allocate_lanes(clips: list[TimelineClip]) -> list[tuple[int, TimelineClip]]:
    """Greedily pack clips onto lanes so none overlap on the same lane.

    Returns ``(lane_index, clip)`` where lane_index starts at 1 (the caller maps
    it to xmeml track 1.. or FCPXML lane -1..). Clips are processed in start order.
    """
    lane_end: list[float] = []  # last end time on each lane
    out: list[tuple[int, TimelineClip]] = []
    for clip in sorted(clips, key=lambda c: (c.start, c.end)):
        placed = False
        for i, end in enumerate(lane_end):
            if clip.start >= end - 1e-6:
                lane_end[i] = clip.end
                out.append((i + 1, clip))
                placed = True
                break
        if not placed:
            lane_end.append(clip.end)
            out.append((len(lane_end), clip))
    return out


def serialize(root: ET.Element, doctype: str) -> str:
    """Pretty-print an ElementTree with an XML declaration and DOCTYPE."""
    ET.indent(root, space="  ")
    body = ET.tostring(root, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n{doctype}\n{body}\n'


class Exporter(ABC):
    """Turn a :class:`Timeline` into interchange text an NLE can import."""

    ext: str = ".txt"

    @abstractmethod
    def export(self, timeline: Timeline) -> str:  # pragma: no cover - interface
        ...

    def write(self, timeline: Timeline, path: str | Path) -> Path:
        path = Path(path)
        path.write_text(self.export(timeline), encoding="utf-8")
        return path
