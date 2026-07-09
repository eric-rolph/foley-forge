"""OpenAI-compatible vision backend.

Talks to any server exposing ``POST {base_url}/chat/completions`` with image content
parts — llama.cpp's ``--server``, Ollama (``/v1``), LM Studio, vLLM, or the OpenAI API
itself. Uses the standard library only (``urllib``) so it needs no extra dependency.
"""

from __future__ import annotations

import base64
import json
import os
import urllib.error
import urllib.request

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
    if not ok:
        return None
    return base64.b64encode(buf.tobytes()).decode("ascii")


class OpenAICompatBackend(CaptionBackend):
    name = "openai"
    description = "OpenAI-compatible vision server (llama.cpp / Ollama / LM Studio / vLLM)."

    def __init__(
        self,
        base_url: str = "http://localhost:8080/v1",
        model: str = "qwen2.5-vl-7b-instruct",
        api_key: str = "",
        max_tokens: int = 512,
        timeout: float = 120.0,
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.max_tokens = max_tokens
        self.timeout = timeout

    def available(self) -> bool:
        return cv2 is not None and bool(self.base_url)

    def caption_frames(self, frames: list[Frame]) -> list[SceneObservation]:
        return [self._caption_one(f) for f in frames]

    def _caption_one(self, frame: Frame) -> SceneObservation:
        b64 = _encode_jpeg_b64(frame.image)
        content: list[dict] = [{"type": "text", "text": USER_PROMPT.format(t=frame.t)}]
        if b64:
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "max_tokens": self.max_tokens,
            "temperature": 0.1,
        }
        try:
            text = self._post(payload)
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            return SceneObservation(
                t=frame.t, description=f"[backend error: {e}]", source=self.name)
        return parse_caption_json(text, frame.t, self.name)

    def _post(self, payload: dict) -> str:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/chat/completions", data=data, method="POST")
        req.add_header("Content-Type", "application/json")
        if self.api_key:
            req.add_header("Authorization", f"Bearer {self.api_key}")
        with urllib.request.urlopen(req, timeout=self.timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
        return body["choices"][0]["message"]["content"]
