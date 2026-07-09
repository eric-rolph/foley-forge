"""FCP7 XML (xmeml v5) exporter.

xmeml is the only interchange that **both DaVinci Resolve and Premiere Pro**
import directly, which makes it foley-forge's primary output. Clips are placed by
integer frame index; the sequence ``<rate>`` (timebase + ntsc flag) tells the NLE
how to interpret those frames.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET

from ..models import Timeline
from ..timecode import seconds_to_frames, xmeml_rate
from .base import Exporter, allocate_lanes, serialize, xmeml_pathurl


def _rate(parent: ET.Element, timebase: int, ntsc: bool, with_ntsc: bool = True) -> None:
    rate = ET.SubElement(parent, "rate")
    ET.SubElement(rate, "timebase").text = str(timebase)
    if with_ntsc:
        ET.SubElement(rate, "ntsc").text = "TRUE" if ntsc else "FALSE"


class FCP7XMLExporter(Exporter):
    ext = ".xml"

    def __init__(self, include_source_video: bool = True):
        self.include_source_video = include_source_video

    def export(self, timeline: Timeline) -> str:
        fps = timeline.fps
        timebase, ntsc = xmeml_rate(fps)
        seq_frames = seconds_to_frames(timeline.duration, fps)

        root = ET.Element("xmeml", version="5")
        seq = ET.SubElement(root, "sequence", id="foley-forge-seq")
        ET.SubElement(seq, "name").text = timeline.name
        ET.SubElement(seq, "duration").text = str(seq_frames)
        _rate(seq, timebase, ntsc)
        media = ET.SubElement(seq, "media")

        file_ids: dict[str, str] = {}   # media path -> file id (define once, ref after)
        counter = {"clip": 0, "file": 0}

        def file_id_for(path: str) -> tuple[str, bool]:
            if path in file_ids:
                return file_ids[path], False
            counter["file"] += 1
            fid = f"file-{counter['file']}"
            file_ids[path] = fid
            return fid, True

        # ---- video track (source clip spanning the timeline) ----
        video = ET.SubElement(media, "video")
        vids = timeline.video_clips
        if self.include_source_video and vids:
            vtrack = ET.SubElement(video, "track")
            for clip in vids:
                self._video_clipitem(
                    vtrack, clip, fps, timebase, ntsc, counter, file_id_for,
                    timeline.width, timeline.height,
                )

        # ---- audio tracks (SFX, packed so nothing overlaps) ----
        audio = ET.SubElement(media, "audio")
        lanes = allocate_lanes(timeline.audio_clips)
        n_tracks = max((ln for ln, _ in lanes), default=0)
        for t in range(1, n_tracks + 1):
            atrack = ET.SubElement(audio, "track")
            for ln, clip in lanes:
                if ln == t:
                    self._audio_clipitem(atrack, clip, fps, timebase, ntsc, counter, file_id_for)

        return serialize(root, "<!DOCTYPE xmeml>")

    def _audio_clipitem(self, track, clip, fps, timebase, ntsc, counter, file_id_for):
        counter["clip"] += 1
        start_f = seconds_to_frames(clip.start, fps)
        end_f = seconds_to_frames(clip.end, fps)
        dur_f = max(1, end_f - start_f)

        item = ET.SubElement(track, "clipitem", id=f"clipitem-{counter['clip']}")
        ET.SubElement(item, "name").text = clip.name
        ET.SubElement(item, "enabled").text = "TRUE"
        ET.SubElement(item, "duration").text = str(dur_f)
        _rate(item, timebase, ntsc)
        ET.SubElement(item, "start").text = str(start_f)
        ET.SubElement(item, "end").text = str(end_f)
        ET.SubElement(item, "in").text = "0"
        ET.SubElement(item, "out").text = str(dur_f)

        fid, first = file_id_for(clip.media_path)
        if first:
            fel = ET.SubElement(item, "file", id=fid)
            ET.SubElement(fel, "name").text = clip.name
            ET.SubElement(fel, "pathurl").text = xmeml_pathurl(clip.media_path)
            _rate(fel, timebase, ntsc, with_ntsc=False)
            ET.SubElement(fel, "duration").text = str(dur_f)
            fmedia = ET.SubElement(fel, "media")
            fa = ET.SubElement(fmedia, "audio")
            ET.SubElement(fa, "channelcount").text = str(clip.channels)
        else:
            ET.SubElement(item, "file", id=fid)

        st = ET.SubElement(item, "sourcetrack")
        ET.SubElement(st, "mediatype").text = "audio"
        ET.SubElement(st, "trackindex").text = "1"

    def _video_clipitem(self, track, clip, fps, timebase, ntsc, counter, file_id_for,
                        width=1920, height=1080):
        counter["clip"] += 1
        start_f = seconds_to_frames(clip.start, fps)
        end_f = seconds_to_frames(clip.end, fps)
        dur_f = max(1, end_f - start_f)

        item = ET.SubElement(track, "clipitem", id=f"clipitem-{counter['clip']}")
        ET.SubElement(item, "name").text = clip.name
        ET.SubElement(item, "enabled").text = "TRUE"
        ET.SubElement(item, "duration").text = str(dur_f)
        _rate(item, timebase, ntsc)
        ET.SubElement(item, "start").text = str(start_f)
        ET.SubElement(item, "end").text = str(end_f)
        ET.SubElement(item, "in").text = "0"
        ET.SubElement(item, "out").text = str(dur_f)

        fid, first = file_id_for(clip.media_path)
        if first:
            fel = ET.SubElement(item, "file", id=fid)
            ET.SubElement(fel, "name").text = clip.name
            ET.SubElement(fel, "pathurl").text = xmeml_pathurl(clip.media_path)
            _rate(fel, timebase, ntsc, with_ntsc=False)
            ET.SubElement(fel, "duration").text = str(dur_f)
            fmedia = ET.SubElement(fel, "media")
            fv = ET.SubElement(fmedia, "video")
            sc = ET.SubElement(fv, "samplecharacteristics")
            _rate(sc, timebase, ntsc, with_ntsc=False)
            ET.SubElement(sc, "width").text = str(width)
            ET.SubElement(sc, "height").text = str(height)
        else:
            ET.SubElement(item, "file", id=fid)


def export_fcp7xml(timeline: Timeline, include_source_video: bool = True) -> str:
    return FCP7XMLExporter(include_source_video).export(timeline)
