# Changelog

All notable changes to foley-forge are documented here. Format loosely follows
[Keep a Changelog](https://keepachangelog.com/); this project uses semantic versioning.

## [0.1.0] — 2026-07-09
### Added
- End-to-end pipeline: ingest → scenes → sample → caption → onsets → fuse → match → export.
- Any-container ingest via `ffprobe`/`ffmpeg`; 16 kHz mono audio extraction.
- Frame sampling with PySceneDetect scene detection (frame-diff fallback when not installed).
- Pluggable caption backends: `mock` (offline heuristic), `openai` (OpenAI-compatible vision server),
  `anthropic` (Claude vision), `opencv5` (experimental PaliGemma2 via `cv.dnn`).
- Audio onset detection (librosa with a dependency-free numpy spectral-flux fallback).
- Event taxonomy + lexical SFX matcher. (CLAP semantic matching is planned — see
  ROADMAP.md — and is not implemented in 0.1; the `use_clap` flag is currently a no-op.)
- Timeline exporters: FCP7 XML (xmeml), FCPXML v1.9, CMX3600 EDL — with correct DF/NDF timecode and
  `file://` media URIs.
- Timestamped scene narrative (`.md`/`.json`) and license-provenance `CREDITS.md`.
- CC0 synthetic starter SFX pack + `index-sfx` to build a manifest from any folder.
- Frame-accurate `timecode` module and a full pytest suite (timecode, exporters, matcher, e2e).

### Known limitations
- `opencv5` backend is a scaffold: it requires OpenCV 5 plus self-exported ONNX graphs and raises a clear
  guidance error until configured.
- CLAP semantic matching is **not implemented** in 0.1 (roadmap); only lexical tag matching runs today.
- Freesound is a **library-only helper** (`foley_forge.sfx.freesound.FreesoundClient`) — there is no
  one-command import yet; bring downloaded files in via `index-sfx`.
- The mock backend is intentionally content-agnostic (motion + onsets), not a real detector.
