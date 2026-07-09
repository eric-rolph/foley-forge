# Roadmap

foley-forge's core is **video → detected interactions → matched SFX → editor timeline**. Everything below
either sharpens that core or extends it into a broader "automated editing" assistant. Priority reflects
*synergy with the SFX engine* (does it reuse the decode + audio-analysis pipeline we already run?) and
*OSS maturity on Windows*.

## v0.1 — shipped (alpha)
- [x] Any-container ingest (`ffprobe`/`ffmpeg`) + 16 kHz mono audio extraction
- [x] Frame sampling + scene-cut detection (PySceneDetect, frame-diff fallback)
- [x] Pluggable caption backends: `mock` (offline), `openai`, `anthropic`, `opencv5` (experimental)
- [x] Audio onset detection (librosa + numpy fallback) for precise cue timing
- [x] Event taxonomy + lexical SFX matcher (CLAP semantic matcher optional)
- [x] Timeline exporters: FCP7 XML (xmeml), FCPXML v1.9, CMX3600 EDL
- [x] Timestamped scene narrative (`.md` / `.json`) + license-provenance `CREDITS.md`
- [x] CC0 synthetic starter SFX pack

## v0.2 — finish the mix (highest synergy)
- [ ] **Loudness normalization + auto-ducking** — `ffmpeg loudnorm` (two-pass → −14 LUFS, −1 dBTP) then
      `sidechaincompress` to duck SFX/music under the speech track. *(command builder already in
      `enhance/loudness.py`; wire an `enhance` CLI step + render.)*
- [ ] **Scene-cue transitions** — auto-place whooshes/risers on detected cuts, beat-aware. *(reuses scenes)*
- [ ] **Beat detection** — `librosa.beat.beat_track` to snap cues/cuts to musical beats. *(scaffold in `enhance/beats.py`)*
- [ ] Interactive review TUI/GUI: accept / reject / swap each cue before export

## v0.3 — the talking-head toolkit
- [ ] **Captions / subtitles** — `whisper.cpp` (CPU) / `faster-whisper` (GPU) → burn-in or SRT
- [ ] **Silence / dead-air trim + jump-cuts** — Silero VAD, auto-editor-style `--margin`
- [ ] **Filler-word removal** — WhisperX word timestamps → cut `um`/`uh` spans

## v0.4 — repurposing
- [ ] **Highlight / Shorts extraction** — scene + transcript scoring → candidate clips
- [ ] **Auto-reframe to vertical** — subject-tracked 16:9 → 9:16 *(highest-risk; OSS options immature)*
- [ ] **Speaker diarization** — pyannote 3.1 (per-speaker SFX/duck lanes)

## Cross-cutting
- [ ] CLAP semantic SFX ranking on by default (precompute embeddings at `index-sfx` time)
- [ ] Confidence-thresholded auto vs. review modes
- [ ] OpenTimelineIO export path (`.[otio]`) for AAF/OTIO round-trip
- [ ] Track the OpenCV 5.1+ `cv.dnn` VLM path (GPU, broader model set) and promote `opencv5` out of experimental
- [ ] Package a one-file desktop build (PyInstaller) with bundled ffmpeg (LGPL) + whisper.cpp CPU binary
