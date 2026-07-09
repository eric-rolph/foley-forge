"""Controlled vocabulary of physical-interaction events.

This single taxonomy is shared by:

* the **caption prompt** (we ask the VLM to label interactions with these keys),
* the **normalizer** (maps a backend's free-text phrase to a canonical key),
* the **matcher** (maps a key to SFX search tags).

Keys are loosely aligned with the AudioSet ontology so a CLAP/tag search over a
general SFX library finds sensible sounds.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Event:
    key: str
    tags: tuple[str, ...]                     # SFX search tags
    keywords: tuple[str, ...] = ()            # phrases that map to this event

    def with_defaults(self) -> Event:
        return self


EVENTS: dict[str, Event] = {
    e.key: e for e in [
        Event("door_slam", ("door", "slam", "close", "bang"),
              ("door slam", "slam the door", "door closes", "shut the door", "door bang", "closing door", "slams shut")),
        Event("knock", ("door", "knock", "rap"),
              ("knock", "knocking", "rapping", "taps on the door")),
        Event("footstep", ("footsteps", "walk", "step"),
              ("footstep", "footsteps", "walking", "steps", "running", "stomp", "walks")),
        Event("punch", ("punch", "hit", "impact", "fist"),
              ("punch", "punches", "strike", "slap", "smack", "hits", "jab")),
        Event("glass_break", ("glass", "break", "shatter"),
              ("glass break", "breaks glass", "shatter", "broken glass", "smash", "shattering")),
        Event("clap", ("clap", "applause", "hands"),
              ("clap", "clapping", "applause", "claps hands")),
        Event("keyboard", ("keyboard", "typing", "keys"),
              ("typing", "keyboard", "types", "typewriter", "keys")),
        Event("splash", ("water", "splash"),
              ("splash", "splashes", "dives into", "pouring water", "water splash")),
        Event("whoosh", ("whoosh", "swipe", "transition"),
              ("whoosh", "swipe", "fast movement", "transition", "swing", "swings", "quick motion")),
        Event("object_drop", ("drop", "thud", "object", "fall"),
              ("drop", "drops", "falls", "fell", "thud", "sets down", "puts down")),
        Event("gunshot", ("gun", "gunshot", "shot"),
              ("gunshot", "gun fires", "shoots", "fires a gun", "gunfire")),
        Event("explosion", ("explosion", "boom", "blast"),
              ("explosion", "explodes", "blast", "boom", "detonation")),
        Event("click", ("click", "button", "switch"),
              ("click", "clicks", "button", "switch", "snap", "presses a button")),
        Event("bell", ("bell", "ring", "ding"),
              ("bell", "rings", "ding", "chime", "dings")),
        Event("phone", ("phone", "ring", "notification"),
              ("phone rings", "ringtone", "incoming call", "notification")),
        Event("engine", ("engine", "car", "motor"),
              ("engine", "car", "motor", "vehicle", "revs", "engine starts")),
        Event("cheer", ("cheer", "crowd", "applause"),
              ("cheer", "crowd", "celebration", "cheering", "crowd roars")),
        Event("impact", ("impact", "hit", "thud", "bang"),
              ("impact", "bang", "crash", "collision", "hits the ground", "crashes")),
        Event("movement", ("movement", "motion", "rustle"),
              ("move", "movement", "motion", "gesture", "moves", "shifts")),
    ]
}

ALL_LABELS: list[str] = list(EVENTS.keys())


def tags_for(label: str) -> tuple[str, ...]:
    ev = EVENTS.get(label)
    if ev:
        return ev.tags
    # Unknown label: use its own tokens as tags.
    return tuple(t for t in label.replace("_", " ").split() if t)


def normalize_label(text: str) -> tuple[str | None, float]:
    """Map a free-text phrase to a canonical event key.

    Returns ``(key, weight)`` where weight in [0,1] reflects how specific the
    match was (longer matched keywords score higher). ``(None, 0.0)`` if nothing
    matched — callers may still keep the raw phrase for a semantic (CLAP) match.
    """
    if not text:
        return None, 0.0
    t = text.lower()

    # Exact canonical key.
    if t in EVENTS:
        return t, 1.0

    best_key: str | None = None
    best_len = 0
    for key, ev in EVENTS.items():
        for kw in (key.replace("_", " "), *ev.keywords):
            # Word-boundary match so short keywords like "car" don't fire inside
            # unrelated words ("scary", "cart"). Whole-word/phrase keywords still
            # match ("slams shut" in "the door slams shut").
            if kw and len(kw) > best_len and re.search(rf"\b{re.escape(kw)}\b", t):
                best_key, best_len = key, len(kw)
    if best_key is None:
        return None, 0.0
    # Longer, more specific phrase -> higher weight (cap at 1.0).
    return best_key, min(1.0, 0.5 + best_len / 24.0)
