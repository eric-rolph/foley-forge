"""EXPERIMENTAL: OpenCV 5 on-device VLM backend (PaliGemma2-3B via cv.dnn).

Reality check (as of OpenCV 5.0, June 2026): OpenCV 5 added real LLM/VLM *execution*
inside ``cv.dnn`` (new ``ENGINE_NEW`` graph engine, ``cv.dnn.Tokenizer``, opt-in
KV-cache), but there is **no** high-level captioning API. The only reference VLM is
Google **PaliGemma2-3B**, run as a hand-assembled three-graph ONNX pipeline:

  1. SigLIP vision encoder  -> 256 image tokens
  2. an embedding layer     -> token embeddings for the text prompt
  3. a Gemma2 decoder       -> logits, decoded in a Python loop

…plus an OpenCV-format tokenizer config (NOT HuggingFace's). It is CPU-only in 5.0
and the reference sample runs without a VLM KV-cache, so it is slow. foley-forge ships
this as an opt-in experimental backend: it verifies your environment and gives precise
setup guidance rather than pretending to work. Track OpenCV 5.1+ for GPU + more models.
"""

from __future__ import annotations

from pathlib import Path

from ..models import Frame, SceneObservation
from .base import CaptionBackend

try:
    import cv2
except ImportError:  # pragma: no cover
    cv2 = None


def _opencv_major() -> int:
    if cv2 is None:
        return 0
    try:
        return int(cv2.__version__.split(".")[0])
    except (ValueError, IndexError):  # pragma: no cover
        return 0


class OpenCV5Backend(CaptionBackend):
    name = "opencv5"
    description = "EXPERIMENTAL PaliGemma2-3B via OpenCV 5 cv.dnn (CPU-only, slow)."

    def __init__(
        self,
        vision_onnx: str = "",
        embed_onnx: str = "",
        decoder_onnx: str = "",
        tokenizer: str = "",
        max_new_tokens: int = 48,
    ):
        self.vision_onnx = vision_onnx
        self.embed_onnx = embed_onnx
        self.decoder_onnx = decoder_onnx
        self.tokenizer = tokenizer
        self.max_new_tokens = max_new_tokens

    def _missing(self) -> list[str]:
        missing = []
        if _opencv_major() < 5:
            missing.append(f"OpenCV >= 5 (found {cv2.__version__ if cv2 else 'none'})")
        for label, p in [
            ("vision_onnx", self.vision_onnx),
            ("embed_onnx", self.embed_onnx),
            ("decoder_onnx", self.decoder_onnx),
            ("tokenizer", self.tokenizer),
        ]:
            if not p or not Path(p).exists():
                missing.append(f"{label} path")
        return missing

    def available(self) -> bool:
        return not self._missing()

    def caption_frames(self, frames: list[Frame]) -> list[SceneObservation]:
        missing = self._missing()
        if missing:
            raise RuntimeError(
                "opencv5 backend is experimental and not configured. Missing: "
                + ", ".join(missing)
                + ".\nExport PaliGemma2-3B to three ONNX graphs (SigLIP vision encoder, "
                "embedding layer, Gemma2 decoder) + an OpenCV-format tokenizer, then set "
                "[backend] vision_onnx/embed_onnx/decoder_onnx/tokenizer. See "
                "opencv/opencv samples/dnn/vlm_inference.py. For dependable captioning use "
                "--backend openai (llama.cpp/Ollama) or --backend anthropic instead."
            )
        # A configured 3-graph decode loop would go here (ENGINE_NEW). Deliberately not
        # implemented against unexported models to avoid claiming untested behavior.
        raise NotImplementedError(
            "opencv5 decode loop is a scaffold pending validated PaliGemma2 ONNX exports "
            "and OpenCV 5.1 GPU support; contributions welcome (see ROADMAP.md)."
        )
