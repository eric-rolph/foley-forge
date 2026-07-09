"""Caption backend registry."""

from __future__ import annotations

from .anthropic_backend import AnthropicBackend
from .base import CaptionBackend
from .mock import MockBackend
from .openai_compat import OpenAICompatBackend
from .opencv5 import OpenCV5Backend

__all__ = [
    "CaptionBackend", "MockBackend", "OpenAICompatBackend",
    "AnthropicBackend", "OpenCV5Backend",
    "get_backend", "list_backends", "BACKEND_NAMES",
]

BACKEND_NAMES = ["mock", "openai", "anthropic", "opencv5"]


def get_backend(name: str, config: dict | None = None) -> CaptionBackend:
    """Instantiate a backend by name with a config dict (see config.example.toml)."""
    config = config or {}
    name = name.lower()
    if name == "mock":
        return MockBackend(
            impact_threshold=float(config.get("impact_threshold", 0.35)))
    if name in ("openai", "openai_compat", "llamacpp", "ollama", "vllm", "lmstudio"):
        return OpenAICompatBackend(
            base_url=config.get("base_url", "http://localhost:8080/v1"),
            model=config.get("model", "qwen2.5-vl-7b-instruct"),
            api_key=config.get("api_key", ""),
        )
    if name == "anthropic":
        return AnthropicBackend(model=config.get("model", "claude-sonnet-5"))
    if name == "opencv5":
        return OpenCV5Backend(
            vision_onnx=config.get("vision_onnx", ""),
            embed_onnx=config.get("embed_onnx", ""),
            decoder_onnx=config.get("decoder_onnx", ""),
            tokenizer=config.get("tokenizer", ""),
        )
    raise ValueError(f"unknown backend: {name!r} (choose from {BACKEND_NAMES})")


def list_backends() -> list[tuple[str, bool, str]]:
    """Return ``(name, available, description)`` for each backend."""
    out = []
    for name in BACKEND_NAMES:
        try:
            b = get_backend(name)
            out.append((name, b.available(), b.description))
        except Exception as e:  # noqa: BLE001
            out.append((name, False, f"error: {e}"))
    return out
