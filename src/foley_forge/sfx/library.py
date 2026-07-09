"""Sound-effect library: load a manifest of assets with license provenance.

Every asset records its license and attribution so the pipeline can honor
obligations (CC0 = free; CC-BY = must credit; CC-BY-NC = exclude from commercial
runs). See ``NOTICE.md`` for policy.
"""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path

_BUNDLED = Path(__file__).resolve().parent.parent / "assets" / "sfx" / "manifest.json"


@dataclass
class SFXAsset:
    id: str
    name: str
    path: str
    tags: list[str] = field(default_factory=list)
    license: str = "CC0-1.0"
    author: str = ""
    source: str = ""
    url: str = ""
    category: str = ""
    duration: float = 0.0

    @property
    def is_cc0(self) -> bool:
        return self.license.upper().startswith("CC0")

    @property
    def is_noncommercial(self) -> bool:
        return "NC" in self.license.upper()

    @property
    def attribution(self) -> str:
        if self.is_cc0:
            return ""
        bits = [self.author or "Unknown"]
        if self.source:
            bits.append(self.source)
        if self.url:
            bits.append(self.url)
        return " — ".join(bits) + f" ({self.license})"


class SFXLibrary:
    def __init__(self, assets: list[SFXAsset] | None = None):
        self.assets: list[SFXAsset] = assets or []

    def __len__(self) -> int:
        return len(self.assets)

    def extend(self, other: SFXLibrary) -> None:
        seen = {a.id for a in self.assets}
        for a in other.assets:
            if a.id not in seen:
                self.assets.append(a)
                seen.add(a.id)

    @classmethod
    def load_manifest(cls, manifest_path: str | Path) -> SFXLibrary:
        manifest_path = Path(manifest_path)
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
        base = manifest_path.parent
        assets: list[SFXAsset] = []
        for entry in data.get("assets", []):
            rel = entry.get("file") or entry.get("path", "")
            path = (base / rel).resolve()
            assets.append(SFXAsset(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                path=str(path),
                tags=[t.lower() for t in entry.get("tags", [])],
                license=entry.get("license", "CC0-1.0"),
                author=entry.get("author", ""),
                source=entry.get("source", ""),
                url=entry.get("url", ""),
                category=entry.get("category", ""),
                duration=float(entry.get("duration", 0.0)) or _wav_duration(path),
            ))
        return cls(assets)

    @classmethod
    def bundled(cls) -> SFXLibrary:
        if _BUNDLED.exists():
            return cls.load_manifest(_BUNDLED)
        return cls([])

    @classmethod
    def from_folder(cls, folder: str | Path, license: str = "CC0-1.0") -> SFXLibrary:
        """Index a folder of audio files, deriving tags from filenames."""
        folder = Path(folder)
        assets: list[SFXAsset] = []
        for path in sorted(folder.rglob("*")):
            if path.suffix.lower() not in (".wav", ".mp3", ".aif", ".aiff", ".flac", ".ogg"):
                continue
            stem = path.stem
            tags = [t for t in stem.replace("-", "_").lower().split("_") if t]
            assets.append(SFXAsset(
                id=stem,
                name=stem.replace("_", " "),
                path=str(path.resolve()),
                tags=tags,
                license=license,
                source=str(folder),
                category="user",
                duration=_wav_duration(path),
            ))
        return cls(assets)

    def to_manifest(self) -> dict:
        return {
            "version": 1,
            "assets": [
                {
                    "id": a.id, "name": a.name, "file": a.path, "tags": a.tags,
                    "license": a.license, "author": a.author, "source": a.source,
                    "url": a.url, "category": a.category, "duration": round(a.duration, 3),
                }
                for a in self.assets
            ],
        }


def _wav_duration(path: str | Path) -> float:
    try:
        with wave.open(str(path), "rb") as w:
            return w.getnframes() / float(w.getframerate() or 1)
    except (wave.Error, OSError, EOFError):
        return 0.0
