# Contributing to foley-forge

Thanks for looking! This is an early-stage tool; issues and PRs are welcome.

## Dev setup
```bash
python -m venv .venv && . .venv/Scripts/activate   # or .venv/bin/activate
pip install -e ".[dev,audio,scenes]"
pytest         # runs the full suite (needs ffmpeg on PATH for the e2e test)
ruff check .
```

## Ground rules
- **Honesty over hype.** Don't claim a backend/feature works if it doesn't. The `opencv5` backend is
  explicitly experimental for a reason — keep capability claims tied to what actually runs.
- **The exporters are the contract.** FCPXML / xmeml / EDL output is what editors import. Any change there
  needs tests asserting exact structure and frame math (`tests/test_*xml.py`, `tests/test_edl.py`).
- **Optional deps stay optional.** Core must run with only `opencv-python` + `numpy` + `typer` + `rich`
  (plus ffmpeg on PATH). Guard `librosa`, `scenedetect`, `anthropic`, `torch`, etc. behind lazy imports and
  graceful fallbacks.
- **Never bundle non-CC0 audio.** See `NOTICE.md`. Only original/CC0 sounds go in `assets/`.
- **Keep it cross-platform.** Paths via `pathlib`; media URIs via the helpers in `exporters/`.

## Adding a caption backend
Implement `foley_forge.backends.base.CaptionBackend` (`available()` + `caption_frames()`), return
`SceneObservation`s, and register it in `backends/__init__.py`. Emit interactions with canonical labels from
`sfx/taxonomy.py` where possible.

## Adding an exporter
Implement `foley_forge.exporters.base.Exporter.export(timeline) -> str`, add a test with a golden fixture,
and wire it into `pipeline.py` / the CLI.
