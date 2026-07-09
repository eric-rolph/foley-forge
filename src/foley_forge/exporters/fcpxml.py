"""FCPXML exporter (targets v1.9 for broad DaVinci Resolve + Final Cut Pro import).

Final Cut Pro imports *only* FCPXML (never xmeml), and DaVinci Resolve reads it too.
Newer DTDs (1.13/1.14) can fail to import into older Resolve builds, so foley-forge
targets a conservative 1.9. Times are rational strings on the format's timescale;
SFX are connected clips on negative lanes beneath the primary storyline item.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..models import Timeline
from ..timecode import fcpxml_frame_duration, fcpxml_tc_format, fcpxml_time
from .base import Exporter, allocate_lanes, fcpxml_src, serialize

FCPXML_VERSION = "1.9"


class FCPXMLExporter(Exporter):
    ext = ".fcpxml"

    def __init__(self, include_source_video: bool = True, audio_role: str = "effects"):
        self.include_source_video = include_source_video
        self.audio_role = audio_role

    def export(self, timeline: Timeline) -> str:
        fps = timeline.fps
        frame_dur = fcpxml_frame_duration(fps)
        seq_dur = fcpxml_time(timeline.duration, fps)

        root = ET.Element("fcpxml", version=FCPXML_VERSION)
        resources = ET.SubElement(root, "resources")
        ET.SubElement(
            resources, "format", id="r1", name="FFVideoFormatDefault",
            frameDuration=frame_dur, width=str(timeline.width), height=str(timeline.height),
        )

        # Register one <asset> per unique media path.
        asset_ids: dict[str, str] = {}
        next_id = [2]

        def asset_for(path: str, name: str, duration: float, has_video: bool) -> str:
            if path in asset_ids:
                return asset_ids[path]
            aid = f"r{next_id[0]}"
            next_id[0] += 1
            asset_ids[path] = aid
            attrs = {
                "id": aid, "name": name, "start": "0s",
                "duration": fcpxml_time(max(duration, 1.0 / fps), fps),
                "hasAudio": "1", "audioSources": "1",
            }
            if has_video:
                attrs.update(hasVideo="1", format="r1", videoSources="1")
            asset = ET.SubElement(resources, "asset", **attrs)
            ET.SubElement(asset, "media-rep", kind="original-media", src=fcpxml_src(path))
            return aid

        library = ET.SubElement(root, "library")
        event = ET.SubElement(library, "event", name=timeline.name)
        project = ET.SubElement(event, "project", name=timeline.name)
        sequence = ET.SubElement(
            project, "sequence", format="r1", duration=seq_dur,
            tcStart="0s", tcFormat=fcpxml_tc_format(fps),
        )
        spine = ET.SubElement(sequence, "spine")

        # Primary storyline item spanning the timeline: the source video, or a gap.
        vids = timeline.video_clips
        if self.include_source_video and vids:
            vclip = vids[0]
            vid = asset_for(vclip.media_path, vclip.name, timeline.duration, has_video=True)
            primary = ET.SubElement(
                spine, "asset-clip", ref=vid, offset="0s", name=vclip.name,
                start="0s", duration=seq_dur,
            )
        else:
            primary = ET.SubElement(
                spine, "gap", name="gap", offset="0s", start="0s", duration=seq_dur,
            )

        # SFX as connected clips on negative lanes so nothing overlaps on one lane.
        for lane, clip in allocate_lanes(timeline.audio_clips):
            aid = asset_for(clip.media_path, clip.name, clip.duration, has_video=False)
            ET.SubElement(
                primary, "asset-clip", ref=aid, lane=str(-lane),
                offset=fcpxml_time(clip.start, fps), name=clip.name,
                start="0s", duration=fcpxml_time(clip.duration, fps),
                audioRole=self.audio_role,
            )

        return serialize(root, "<!DOCTYPE fcpxml>")


def export_fcpxml(timeline: Timeline, include_source_video: bool = True,
                  audio_role: str = "effects") -> str:
    return FCPXMLExporter(include_source_video, audio_role).export(timeline)
