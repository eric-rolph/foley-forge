"""Timeline exporters and a small dispatch layer."""

from __future__ import annotations

from pathlib import Path

from ..models import Timeline
from .base import Exporter
from .edl import EDLExporter, export_edl
from .fcp7xml import FCP7XMLExporter, export_fcp7xml
from .fcpxml import FCPXMLExporter, export_fcpxml

__all__ = [
    "Exporter",
    "FCP7XMLExporter", "FCPXMLExporter", "EDLExporter",
    "export_fcp7xml", "export_fcpxml", "export_edl",
    "write_exports", "FORMAT_FILENAMES",
]

# Output filename per format id.
FORMAT_FILENAMES = {
    "fcp7xml": "drop.xml",
    "fcpxml": "drop.fcpxml",
    "edl": "drop.edl",
    "otio": "drop.otio",
}


def _exporter(fmt: str, include_source_video: bool, audio_role: str) -> Exporter:
    if fmt == "fcp7xml":
        return FCP7XMLExporter(include_source_video=include_source_video)
    if fmt == "fcpxml":
        return FCPXMLExporter(include_source_video=include_source_video, audio_role=audio_role)
    if fmt == "edl":
        return EDLExporter()
    raise ValueError(f"unknown export format: {fmt!r}")


def write_exports(
    timeline: Timeline,
    outdir: str | Path,
    formats: list[str],
    include_source_video: bool = True,
    audio_role: str = "effects",
) -> dict[str, Path]:
    """Write each requested format into ``outdir``; return ``{fmt: path}``."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    written: dict[str, Path] = {}
    for fmt in formats:
        if fmt == "otio":
            written["otio"] = _write_otio(timeline, outdir / FORMAT_FILENAMES["otio"])
            continue
        exporter = _exporter(fmt, include_source_video, audio_role)
        path = outdir / FORMAT_FILENAMES.get(fmt, f"drop{exporter.ext}")
        exporter.write(timeline, path)
        written[fmt] = path
    return written


def _write_otio(timeline: Timeline, path: Path) -> Path:
    """Optional OpenTimelineIO export (requires the ``otio`` extra)."""
    try:
        import opentimelineio as otio
    except ImportError as e:  # pragma: no cover - optional dep
        raise RuntimeError(
            "OTIO export needs the optional dependency: pip install 'foley-forge[otio]'"
        ) from e

    fps = timeline.fps
    tl = otio.schema.Timeline(name=timeline.name)
    track = otio.schema.Track(name="SFX", kind=otio.schema.TrackKind.Audio)
    tl.tracks.append(track)
    cursor = 0.0
    for clip in sorted(timeline.audio_clips, key=lambda c: c.start):
        if clip.start > cursor:
            gap = clip.start - cursor
            track.append(otio.schema.Gap(
                source_range=otio.opentime.TimeRange(
                    otio.opentime.RationalTime(0, fps),
                    otio.opentime.RationalTime(round(gap * fps), fps),
                )
            ))
        track.append(otio.schema.Clip(
            name=clip.name,
            media_reference=otio.schema.ExternalReference(
                target_url=Path(clip.media_path).resolve().as_uri()
            ),
            source_range=otio.opentime.TimeRange(
                otio.opentime.RationalTime(0, fps),
                otio.opentime.RationalTime(max(1, round(clip.duration * fps)), fps),
            ),
        ))
        cursor = clip.end
    otio.adapters.write_to_file(tl, str(path))
    return path
