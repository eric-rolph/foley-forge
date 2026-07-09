"""Generate foley-forge's bundled CC0 starter sound pack.

These are original, procedurally-synthesized sounds — genuinely public-domain
(CC0), so they can be redistributed with the tool. Run to (re)create the WAVs and
manifest under ``src/foley_forge/assets/sfx/``.

    python scripts/generate_starter_sfx.py

Deterministic (seeded) so regenerated files are byte-stable.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

SR = 44100
rng = np.random.default_rng(42)
ASSETS = Path(__file__).resolve().parent.parent / "src" / "foley_forge" / "assets" / "sfx"


def _norm(y: np.ndarray, peak: float = 0.9) -> np.ndarray:
    m = float(np.max(np.abs(y))) or 1.0
    return (y / m * peak).astype(np.float32)


def _t(dur: float) -> np.ndarray:
    return np.arange(int(dur * SR)) / SR


def whoosh(dur: float, hard: bool = False) -> np.ndarray:
    n = int(dur * SR)
    y = rng.standard_normal(n) * np.hanning(n)
    k = 4 if hard else 12
    y = np.convolve(y, np.ones(k) / k, mode="same")
    return _norm(y, 0.7)


def thud(dur: float = 0.32, freq: float = 80.0, rate: float = 14.0) -> np.ndarray:
    t = _t(dur)
    y = np.sin(2 * np.pi * freq * t) * np.exp(-t * rate)
    c = int(0.006 * SR)
    y[:c] += rng.standard_normal(c) * 0.6 * np.exp(-np.arange(c) / (0.002 * SR))
    return _norm(y)


def hit(dur: float = 0.25) -> np.ndarray:
    t = _t(dur)
    click = rng.standard_normal(len(t)) * np.exp(-t * 60)
    body = np.sin(2 * np.pi * 140 * t) * np.exp(-t * 22)
    return _norm(click * 0.6 + body)


def boom(dur: float = 0.85) -> np.ndarray:
    t = _t(dur)
    y = np.sin(2 * np.pi * 45 * t) * np.exp(-t * 4)
    y += rng.standard_normal(len(t)) * np.exp(-t * 8) * 0.3
    return _norm(y)


def click(dur: float = 0.05) -> np.ndarray:
    t = _t(dur)
    y = rng.standard_normal(len(t)) * np.exp(-t * 120)
    y += np.sin(2 * np.pi * 2000 * t) * np.exp(-t * 90) * 0.3
    return _norm(y, 0.7)


def ding(dur: float = 0.6) -> np.ndarray:
    t = _t(dur)
    y = np.sin(2 * np.pi * 880 * t) * np.exp(-t * 5)
    y += np.sin(2 * np.pi * 1760 * t) * np.exp(-t * 7) * 0.3
    return _norm(y, 0.7)


def footstep(dur: float = 0.18) -> np.ndarray:
    t = _t(dur)
    y = rng.standard_normal(len(t)) * np.exp(-t * 30)
    y = np.convolve(y, np.ones(20) / 20, mode="same")
    y += np.sin(2 * np.pi * 90 * t) * np.exp(-t * 30) * 0.5
    return _norm(y)


def glass(dur: float = 0.5) -> np.ndarray:
    t = _t(dur)
    n = len(t)
    y = rng.standard_normal(n) * np.exp(-t * 10)
    for f in (3200, 4100, 5300, 6400):
        y += np.sin(2 * np.pi * f * t) * np.exp(-t * float(rng.uniform(8, 16))) * 0.15
    idx = rng.integers(0, n, size=40)
    y[idx] += rng.standard_normal(40) * 0.8
    return _norm(y, 0.8)


def splash(dur: float = 0.5) -> np.ndarray:
    t = _t(dur)
    env = np.exp(-t * 6) * (1 - np.exp(-t * 80))
    y = rng.standard_normal(len(t)) * env
    y = np.convolve(y, np.ones(6) / 6, mode="same")
    return _norm(y, 0.7)


def clap(dur: float = 0.12) -> np.ndarray:
    t = _t(dur)
    y = rng.standard_normal(len(t)) * np.exp(-t * 55)
    y = np.convolve(y, np.ones(3) / 3, mode="same")
    return _norm(y, 0.8)


def knock(dur: float = 0.28) -> np.ndarray:
    t = _t(dur)
    n = len(t)
    y = np.zeros(n)
    for start in (0.0, 0.14):
        s = int(start * SR)
        seg = np.sin(2 * np.pi * 120 * t) * np.exp(-t * 30)
        y[s:] += seg[: n - s]
    y += rng.standard_normal(n) * np.exp(-t * 40) * 0.2
    return _norm(y)


# id, display name, generator, tags, category
SOUNDS = [
    ("whoosh_soft", "Whoosh (soft)", lambda: whoosh(0.55),
     ["whoosh", "swipe", "transition", "movement", "swish"], "transition"),
    ("whoosh_hard", "Whoosh (hard)", lambda: whoosh(0.35, hard=True),
     ["whoosh", "swipe", "swing", "transition", "fast"], "transition"),
    ("impact_thud", "Impact thud", lambda: thud(),
     ["impact", "thud", "drop", "object", "fall", "bang", "door", "slam"], "impact"),
    ("impact_hit", "Impact hit", lambda: hit(),
     ["impact", "hit", "punch", "fist", "bang", "smack"], "impact"),
    ("boom_low", "Boom (low)", lambda: boom(),
     ["boom", "explosion", "blast", "gun", "gunshot", "shot", "impact"], "impact"),
    ("click_soft", "Click", lambda: click(),
     ["click", "button", "switch", "keyboard", "typing", "keys", "snap"], "ui"),
    ("bell_ding", "Bell ding", lambda: ding(),
     ["bell", "ring", "ding", "chime", "phone", "notification"], "ui"),
    ("footstep", "Footstep", lambda: footstep(),
     ["footstep", "footsteps", "walk", "step"], "foley"),
    ("glass_break", "Glass break", lambda: glass(),
     ["glass", "break", "shatter", "smash"], "foley"),
    ("splash", "Splash", lambda: splash(),
     ["water", "splash"], "foley"),
    ("clap", "Clap", lambda: clap(),
     ["clap", "applause", "hands", "cheer", "crowd"], "foley"),
    ("knock", "Knock", lambda: knock(),
     ["door", "knock", "rap"], "foley"),
]


def write_wav(path: Path, y: np.ndarray) -> None:
    data = (np.clip(y, -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(data.tobytes())


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    assets = []
    for sid, name, gen, tags, category in SOUNDS:
        y = gen()
        path = ASSETS / f"{sid}.wav"
        write_wav(path, y)
        assets.append({
            "id": sid,
            "name": name,
            "file": f"{sid}.wav",
            "tags": tags,
            "license": "CC0-1.0",
            "author": "foley-forge",
            "source": "synthesized (scripts/generate_starter_sfx.py)",
            "url": "",
            "category": category,
            "duration": round(len(y) / SR, 3),
        })
        print(f"  wrote {path.name}  ({len(y) / SR:.2f}s)")

    manifest = {"version": 1, "generator": "generate_starter_sfx.py", "assets": assets}
    (ASSETS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"wrote manifest.json with {len(assets)} sounds -> {ASSETS}")


if __name__ == "__main__":
    main()
