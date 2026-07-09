"""Freesound expansion — bring your own API key.

foley-forge never ships a Freesound key: the Freesound API is free for
**non-commercial** use only, and each sound carries its own CC license. This client
searches Free Cultural Works (CC0 + CC-BY) by default, downloads previews with a
token, and records attribution for every non-CC0 sound. Original-file download needs
OAuth2 (documented in Freesound's API), which we surface but don't automate.

Requires the ``freesound`` extra (``requests``).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

FREESOUND_SEARCH = "https://freesound.org/apiv2/search/text/"

# Freesound's exact license filter values.
LICENSE_FILTERS = {
    "cc0": 'license:"Creative Commons 0"',
    "cc-by": 'license:"Attribution"',
    "cc-by-nc": 'license:"Attribution NonCommercial"',
}


@dataclass
class FreesoundResult:
    id: int
    name: str
    license: str
    tags: list[str]
    preview_url: str
    author: str
    url: str
    duration: float


class FreesoundClient:
    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("Freesound requires your own API key (see NOTICE.md).")
        self.api_key = api_key

    def search(
        self,
        query: str,
        licenses: tuple[str, ...] = ("cc0", "cc-by"),
        page_size: int = 15,
    ) -> list[FreesoundResult]:
        import requests  # optional dep

        filt = " OR ".join(LICENSE_FILTERS[k] for k in licenses if k in LICENSE_FILTERS)
        params = {
            "query": query,
            "filter": f"({filt})" if filt else None,
            "fields": "id,name,license,tags,previews,username,url,duration",
            "page_size": page_size,
            "token": self.api_key,
        }
        params = {k: v for k, v in params.items() if v is not None}
        resp = requests.get(FREESOUND_SEARCH, params=params, timeout=30)
        resp.raise_for_status()
        results = []
        for r in resp.json().get("results", []):
            results.append(FreesoundResult(
                id=r["id"],
                name=r.get("name", str(r["id"])),
                license=r.get("license", ""),
                tags=r.get("tags", []),
                preview_url=(r.get("previews", {}) or {}).get("preview-hq-mp3", ""),
                author=r.get("username", ""),
                url=r.get("url", ""),
                duration=float(r.get("duration", 0.0)),
            ))
        return results

    def download_preview(self, result: FreesoundResult, out_dir: str | Path) -> Path | None:
        """Download the standard preview mp3 (token auth). Returns the saved path."""
        import requests

        if not result.preview_url:
            return None
        out_dir = Path(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out = out_dir / f"freesound_{result.id}.mp3"
        resp = requests.get(result.preview_url, params={"token": self.api_key}, timeout=60)
        resp.raise_for_status()
        out.write_bytes(resp.content)
        return out


def attribution_line(result: FreesoundResult) -> str:
    """CC-BY credit string; empty for CC0."""
    if "0" in result.license and "Creative Commons 0" in result.license:
        return ""
    return f'"{result.name}" by {result.author} — {result.url} ({result.license})'
