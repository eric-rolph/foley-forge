import wave

import numpy as np

from foley_forge.audio.onsets import _onsets_numpy, detect_onsets
from foley_forge.backends import get_backend, list_backends
from foley_forge.models import Frame


def _write_click_wav(path, clicks=(0.5, 1.0, 1.5), sr=22050, dur=2.0):
    n = int(dur * sr)
    y = np.zeros(n, dtype=np.float32)
    t = np.arange(n) / sr
    for c in clicks:
        s = int(c * sr)
        seg = np.exp(-(np.arange(n - s)) / (0.01 * sr)) * np.sin(2 * np.pi * 900 * t[: n - s])
        y[s:] += seg
    data = (np.clip(y, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sr)
        w.writeframes(data.tobytes())


def test_onsets_numpy_finds_clicks():
    sr = 22050
    y = np.zeros(int(2.0 * sr), dtype=np.float32)
    for c in (0.5, 1.0, 1.5):
        s = int(c * sr)
        y[s:s + 200] += np.hanning(200).astype(np.float32)
    onsets = _onsets_numpy(y, sr)
    assert len(onsets) >= 2
    assert min(abs(o - 0.5) for o in onsets) < 0.06


def test_detect_onsets_end_to_end(tmp_path):
    wav = tmp_path / "clicks.wav"
    _write_click_wav(wav)
    onsets = detect_onsets(str(wav))
    assert len(onsets) >= 2
    assert min(onsets) < 0.7


def test_mock_backend_detects_motion_and_cuts():
    black = np.zeros((120, 160, 3), dtype=np.uint8)
    white = np.full((120, 160, 3), 255, dtype=np.uint8)
    frames = [
        Frame(index=0, t=0.0, image=black),
        Frame(index=1, t=0.5, image=black.copy()),
        Frame(index=2, t=1.0, image=white, is_cut=True),   # big change + cut
        Frame(index=3, t=1.5, image=white.copy()),
    ]
    backend = get_backend("mock")
    obs = backend.caption_frames(frames)
    assert len(obs) == 4
    labels = {i.label for o in obs for i in o.interactions}
    assert "whoosh" in labels          # from the cut
    assert labels & {"impact", "movement"}   # from the motion


def test_list_backends_reports_mock_available():
    names = {n: avail for n, avail, _ in list_backends()}
    assert names["mock"] is True
