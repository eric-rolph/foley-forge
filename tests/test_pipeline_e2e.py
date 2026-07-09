"""End-to-end: synthesize a clip, run the full pipeline offline, check outputs."""

import shutil
import xml.etree.ElementTree as ET

import pytest

from foley_forge.config import Config
from foley_forge.pipeline import run

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None, reason="ffmpeg not on PATH")


@requires_ffmpeg
def test_full_pipeline_offline(sample_video, tmp_path):
    cfg = Config()               # defaults: mock backend, all three exports
    out = tmp_path / "out"
    summary = run(str(sample_video), cfg, out)

    # Files written.
    for name in ("drop.xml", "drop.fcpxml", "drop.edl",
                 "scene_narrative.md", "scene_narrative.json", "CREDITS.md"):
        assert (out / name).exists(), f"missing {name}"

    # The mock backend + testsrc2 motion should yield at least one placed cue.
    assert summary["cues"] >= 1
    assert summary["placed"] >= 1

    # Audio clicks (once/sec) should produce onsets.
    assert summary["onsets"] >= 1

    # drop.xml is valid xmeml with audio clip(s).
    text = (out / "drop.xml").read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines()
             if not ln.startswith("<?xml") and not ln.startswith("<!DOCTYPE")]
    root = ET.fromstring("\n".join(lines))
    assert root.tag == "xmeml"
    assert len(root.findall("./sequence/media/audio/track/clipitem")) >= 1


@requires_ffmpeg
def test_probe_reads_metadata(sample_video):
    from foley_forge.ingest import probe

    info = probe(str(sample_video))
    assert info.width == 320 and info.height == 240
    assert info.has_audio
    assert 28 <= info.fps <= 31
    assert info.duration > 2.0
