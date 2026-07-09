"""Offline heuristic backend — the zero-dependency default.

It does not "understand" the scene; it measures inter-frame motion (mean absolute
difference of down-scaled grayscale frames) and flags high-motion frames as impacts
and scene cuts as whooshes. Combined with audio-onset snapping in the pipeline, this
produces a real, editable SFX timeline with **no model and no GPU** — which also makes
the whole tool testable in CI.
"""

from __future__ import annotations

import numpy as np

from ..models import Frame, Interaction, SceneObservation
from .base import CaptionBackend

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def _gray_small(image) -> np.ndarray | None:
    if image is None:
        return None
    arr = np.asarray(image)
    if arr.ndim == 3 and cv2 is not None:
        arr = cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY)
    elif arr.ndim == 3:
        arr = arr.mean(axis=2)
    if cv2 is not None:
        arr = cv2.resize(arr.astype("float32"), (64, 64))
    else:  # pragma: no cover - cv2 always present in core deps
        arr = arr.astype("float32")
    return arr


class MockBackend(CaptionBackend):
    name = "mock"
    description = "Offline heuristic (motion + cuts). No model, no GPU."

    def __init__(self, impact_threshold: float = 0.35):
        self.impact_threshold = impact_threshold

    def caption_frames(self, frames: list[Frame]) -> list[SceneObservation]:
        grays = [_gray_small(f.image) for f in frames]
        deltas: list[float] = []
        for i in range(len(frames)):
            if i == 0 or grays[i] is None or grays[i - 1] is None:
                deltas.append(0.0)
            else:
                deltas.append(float(np.mean(np.abs(grays[i] - grays[i - 1]))))

        peak = max(deltas) or 1.0
        observations: list[SceneObservation] = []
        for f, d in zip(frames, deltas, strict=False):
            score = d / peak
            interactions: list[Interaction] = []
            if f.is_cut:
                interactions.append(Interaction(
                    label="whoosh", confidence=0.6, raw="scene cut"))
            if score > self.impact_threshold:
                label = "impact" if score > 0.6 else "movement"
                interactions.append(Interaction(
                    label=label,
                    confidence=round(min(0.95, 0.40 + score * 0.5), 3),
                    raw=f"motion={score:.2f}",
                ))
            desc = f"Frame at {f.t:.2f}s — motion {score:.2f}" + (" (cut)" if f.is_cut else "")
            observations.append(SceneObservation(
                t=f.t, description=desc, interactions=interactions, source=self.name))
        return observations
