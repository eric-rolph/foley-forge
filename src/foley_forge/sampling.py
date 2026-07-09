"""Frame sampling + scene-cut detection.

We caption a *sparse* set of frames (captioning is the expensive step): a regular
grid at ``sample_fps`` plus one frame at each detected scene cut. PySceneDetect is
used when installed; otherwise a lightweight grayscale frame-difference detector.
"""

from __future__ import annotations

import numpy as np

from .ingest import VideoInfo
from .models import Frame

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def detect_scenes(path: str, threshold: float = 27.0) -> list[float]:
    """Return scene-cut times (seconds). PySceneDetect if available, else fallback."""
    try:
        from scenedetect import ContentDetector, SceneManager, open_video

        video = open_video(str(path))
        sm = SceneManager()
        sm.add_detector(ContentDetector(threshold=threshold))
        sm.detect_scenes(video)
        scenes = sm.get_scene_list()
        # Each scene's start (skip 0.0) is a cut point.
        return [s[0].get_seconds() for s in scenes if s[0].get_seconds() > 0.01]
    except ImportError:
        return _detect_scenes_framediff(path)


def _detect_scenes_framediff(path: str, z: float = 3.0, min_gap: float = 0.4) -> list[float]:
    """Fallback: flag frames whose grayscale histogram jumps far above the running mean."""
    if cv2 is None:
        return []
    cap = cv2.VideoCapture(str(path))
    fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
    prev = None
    diffs: list[tuple[float, float]] = []
    idx = 0
    while True:
        ok, frame = cap.read()
        if not ok:
            break
        small = cv2.resize(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), (64, 64)).astype("float32")
        if prev is not None:
            diffs.append((idx / fps, float(np.mean(np.abs(small - prev)))))
        prev = small
        idx += 1
    cap.release()
    if not diffs:
        return []

    vals = np.array([val for _, val in diffs])
    mean, std = float(vals.mean()), float(vals.std()) or 1.0
    cuts: list[float] = []
    for t, v in diffs:
        if v > mean + z * std and (not cuts or t - cuts[-1] >= min_gap):
            cuts.append(t)
    return cuts


def sample_frames(
    info: VideoInfo,
    sample_fps: float = 1.5,
    max_frames: int = 400,
    include_cuts: bool = True,
    cut_times: list[float] | None = None,
) -> list[Frame]:
    """Grab frames at a regular grid + at each cut, capped to ``max_frames``."""
    if cv2 is None:  # pragma: no cover
        raise RuntimeError("OpenCV (cv2) is required for frame sampling")
    max_frames = max(1, max_frames)   # 0/negative would divide-by-zero / empty the grid
    duration = info.duration or 0.0
    cut_times = cut_times or []

    grid = list(np.arange(0.0, max(duration, 1e-3), 1.0 / max(sample_fps, 1e-3)))
    cut_set = set(round(t, 3) for t in cut_times) if include_cuts else set()
    stamps = sorted(set(round(t, 3) for t in grid) | cut_set)

    if len(stamps) > max_frames:
        step = len(stamps) / max_frames
        stamps = [stamps[int(i * step)] for i in range(max_frames)]

    cap = cv2.VideoCapture(str(info.path))
    frames: list[Frame] = []
    for i, t in enumerate(stamps):
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, image = cap.read()
        if not ok or image is None:
            continue
        frames.append(Frame(index=i, t=float(t), image=image, is_cut=round(t, 3) in cut_set))
    cap.release()
    return frames
