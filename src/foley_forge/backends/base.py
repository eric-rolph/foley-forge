"""Caption backend interface + shared prompt/parse helpers."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from ..models import Frame, Interaction, SceneObservation
from ..sfx.taxonomy import ALL_LABELS, normalize_label

SYSTEM_PROMPT = (
    "You are a foley editor's assistant. Look at a single video frame and report "
    "physical interactions that would produce a distinct SOUND. Respond with STRICT "
    "JSON only, no prose, in this schema:\n"
    '{"description": "<one short sentence>", "interactions": '
    '[{"label": "<one of the allowed labels>", "object": "<thing>", "confidence": 0.0}]}\n'
    "Allowed labels: " + ", ".join(ALL_LABELS) + ". "
    "If a sound-producing action is ambiguous, pick the closest label and lower the "
    "confidence. If nothing would make a sound, return an empty interactions list."
)

USER_PROMPT = "Frame at t={t:.2f}s. What sound-producing physical interactions are visible?"


def parse_caption_json(text: str, t: float, source: str) -> SceneObservation:
    """Parse a backend's JSON reply into a :class:`SceneObservation` (tolerant)."""
    description = ""
    interactions: list[Interaction] = []
    obj = _loads_lenient(text)
    if isinstance(obj, dict):
        description = str(obj.get("description", "")).strip()
        for raw in obj.get("interactions", []) or []:
            if not isinstance(raw, dict):
                continue
            raw_label = str(raw.get("label", "")).strip()
            key, _weight = normalize_label(raw_label)
            try:
                conf = float(raw.get("confidence", 0.5))
            except (TypeError, ValueError):
                conf = 0.5
            interactions.append(Interaction(
                label=key or raw_label or "movement",
                confidence=max(0.0, min(1.0, conf)),
                obj=str(raw.get("object", "")).strip(),
                raw=raw_label,
            ))
    else:
        description = text.strip()[:200]
    return SceneObservation(t=t, description=description, interactions=interactions, source=source)


def _loads_lenient(text: str):
    """Best-effort JSON extraction: handles ```json fences and surrounding prose."""
    text = text.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start, end = text.find("{"), text.rfind("}")
    if 0 <= start < end:
        try:
            return json.loads(text[start:end + 1])
        except json.JSONDecodeError:
            return None
    return None


class CaptionBackend(ABC):
    """Turn sampled frames into scene observations with labeled interactions."""

    name: str = "base"
    description: str = ""

    def available(self) -> bool:
        """Whether this backend can run right now (deps + config present)."""
        return True

    @abstractmethod
    def caption_frames(self, frames: list[Frame]) -> list[SceneObservation]:
        ...
