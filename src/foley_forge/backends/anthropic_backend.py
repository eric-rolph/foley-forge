"""Anthropic (Claude vision) caption backend — optional cloud path.

Requires ``pip install 'foley-forge[cloud]'`` and ``ANTHROPIC_API_KEY``. Useful when
you want strong scene understanding without hosting a local model.
"""

from __future__ import annotations

import base64
import os

from ..models import Frame, SceneObservation
from .base import SYSTEM_PROMPT, USER_PROMPT, CaptionBackend, parse_caption_json

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def _encode_jpeg_b64(image, max_side: int = 768) -> str | None:
    if image is None or cv2 is None:
        return None
    import numpy as np
    arr = np.asarray(image)
    h, w = arr.shape[:2]
    scale = max_side / max(h, w)
    if scale < 1.0:
        arr = cv2.resize(arr, (int(w * scale), int(h * scale)))
    ok, buf = cv2.imencode(".jpg", arr, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
    return base64.b64encode(buf.tobytes()).decode("ascii") if ok else None


class AnthropicBackend(CaptionBackend):
    name = "anthropic"
    description = "Claude vision (cloud). Needs [cloud] extra + ANTHROPIC_API_KEY."

    def __init__(self, model: str = "claude-sonnet-5", max_tokens: int = 512):
        self.model = model
        self.max_tokens = max_tokens
        self._client = None

    def available(self) -> bool:
        if cv2 is None or not os.environ.get("ANTHROPIC_API_KEY"):
            return False
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False
        return True

    def _get_client(self):
        if self._client is None:
            import anthropic
            self._client = anthropic.Anthropic()
        return self._client

    def caption_frames(self, frames: list[Frame]) -> list[SceneObservation]:
        client = self._get_client()
        out: list[SceneObservation] = []
        for f in frames:
            b64 = _encode_jpeg_b64(f.image)
            content: list[dict] = [{"type": "text", "text": USER_PROMPT.format(t=f.t)}]
            if b64:
                content.append({
                    "type": "image",
                    "source": {"type": "base64", "media_type": "image/jpeg", "data": b64},
                })
            try:
                msg = client.messages.create(
                    model=self.model,
                    max_tokens=self.max_tokens,
                    system=SYSTEM_PROMPT,
                    messages=[{"role": "user", "content": content}],
                )
                text = "".join(
                    block.text for block in msg.content if getattr(block, "type", "") == "text"
                )
            except Exception as e:  # noqa: BLE001 - surface any SDK/network error as an observation
                out.append(SceneObservation(
                    t=f.t, description=f"[anthropic error: {e}]", source=self.name))
                continue
            out.append(parse_caption_json(text, f.t, self.name))
        return out
