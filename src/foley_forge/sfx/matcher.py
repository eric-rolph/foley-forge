"""Match a detected event label to a sound-effect asset.

Today this is purely **lexical**: overlap between the event's taxonomy tags and each
asset's tags (with a conservative partial-token fallback). A **semantic (CLAP)** layer
— embedding the event phrase and ranking assets by cosine similarity to precomputed
audio embeddings — is on the roadmap (the ``clap`` extra + ``use_clap`` flag are
reserved for it) but is **not implemented** yet.

Commercial runs exclude non-commercial (CC-BY-NC) assets and prefer CC0.
"""

from __future__ import annotations

from ..models import SFXMatch
from .library import SFXAsset, SFXLibrary
from .taxonomy import tags_for

_FALLBACK_TAGS = ("impact", "whoosh", "thud", "hit")


def _lexical_score(event_tags: set[str], asset: SFXAsset) -> float:
    if not event_tags:
        return 0.0
    at = set(asset.tags)
    inter = event_tags & at
    if inter:
        score = len(inter) / len(event_tags)
    else:
        # Partial-token fallback, but only for longer tokens (so "car" doesn't match
        # "cardboard") and scored below the weakest exact-intersection so a partial
        # match never outranks a real tag hit.
        score = 0.0
        for e in event_tags:
            for a in at:
                if len(e) >= 5 and (e in a or a in e):
                    score = max(score, 0.25)
    return min(1.0, score)


def match_event(
    label: str,
    library: SFXLibrary,
    min_score: float = 0.2,
    commercial: bool = True,
) -> SFXMatch | None:
    """Return the best SFX for an event label, or a fallback, or None if library empty."""
    candidates = [
        a for a in library.assets
        if not (commercial and a.is_noncommercial)
    ]
    if not candidates:
        return None

    event_tags = set(tags_for(label))
    scored = sorted(
        ((_lexical_score(event_tags, a), a) for a in candidates),
        key=lambda x: (x[0], -x[1].duration),
        reverse=True,
    )
    best_score, best = scored[0]

    if best_score >= min_score:
        return _to_match(best, best_score, "lexical")

    # Fallback: nearest generic impact/whoosh so every cue still gets a sound.
    fb_tags = set(_FALLBACK_TAGS)
    fb_scored = sorted(
        ((_lexical_score(fb_tags, a), a) for a in candidates),
        key=lambda x: x[0], reverse=True,
    )
    fb_score, fb = fb_scored[0]
    if fb_score > 0:
        return _to_match(fb, fb_score * 0.5, "fallback")
    # Last resort: first asset.
    return _to_match(candidates[0], 0.1, "fallback")


def _to_match(asset: SFXAsset, score: float, match_type: str) -> SFXMatch:
    return SFXMatch(
        asset_id=asset.id,
        name=asset.name,
        path=asset.path,
        license=asset.license,
        attribution=asset.attribution,
        score=round(float(score), 3),
        match_type=match_type,
        duration=asset.duration,
    )
