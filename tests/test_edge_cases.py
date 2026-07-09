"""Regression tests for edge cases surfaced by the adversarial review."""

from foley_forge.config import Config
from foley_forge.ingest import VideoInfo
from foley_forge.models import Interaction, SceneObservation
from foley_forge.pipeline import fuse
from foley_forge.sampling import sample_frames
from foley_forge.sfx import SFXLibrary, match_event
from foley_forge.sfx.library import SFXAsset


def test_sample_frames_max_frames_zero_does_not_crash():
    # max_frames=0 previously caused ZeroDivisionError; now clamped to >=1.
    info = VideoInfo(path="does_not_exist.mp4", fps=30.0, duration=1.0,
                     width=320, height=240, has_audio=False)
    frames = sample_frames(info, sample_fps=1.5, max_frames=0)
    assert frames == []          # no decodable frames, but no crash


def test_config_clamps_max_frames(tmp_path):
    cfg_file = tmp_path / "c.toml"
    cfg_file.write_text("[sampling]\nmax_frames = 0\n", encoding="utf-8")
    assert Config.load(cfg_file).max_frames == 1


def test_fuse_keeps_separable_cues():
    # door_slam@1.0 and glass_break@1.3 are 0.30s apart (> min_gap 0.20) and must
    # both survive; the generic impact@1.05 is suppressed by the nearby door_slam.
    obs = [
        SceneObservation(t=1.00, description="", interactions=[Interaction("door_slam", 0.9)]),
        SceneObservation(t=1.05, description="", interactions=[Interaction("impact", 0.5)]),
        SceneObservation(t=1.30, description="", interactions=[Interaction("glass_break", 0.9)]),
    ]
    cues = fuse(obs, onsets=[], config=Config())
    events = sorted(c.event for c in cues)
    assert events == ["door_slam", "glass_break"]


def test_matcher_no_false_partial_short_tag():
    # "engine" carries the short tag "car"; it must NOT match an asset tagged
    # "cardboard" (the old len>=3 substring rule did). The exact "engine" wins.
    lib = SFXLibrary([
        SFXAsset(id="box", name="box", path="box.wav", tags=["cardboard"]),
        SFXAsset(id="eng", name="engine", path="eng.wav", tags=["engine"]),
    ])
    m = match_event("engine", lib)
    assert m.asset_id == "eng"
    assert m.match_type == "lexical"
