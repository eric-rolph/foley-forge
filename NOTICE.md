# NOTICE — third-party licenses & sound-library policy

## foley-forge code
MIT (see `LICENSE`).

## Bundled sound effects
`src/foley_forge/assets/sfx/*.wav` are **original works** synthesized by `scripts/generate_starter_sfx.py`
and dedicated to the public domain under **Creative Commons CC0 1.0**. Per-file provenance is recorded in
`src/foley_forge/assets/sfx/manifest.json`.

## Runtime dependencies (installed separately, not redistributed here)
| Component | License | Notes |
|-----------|---------|-------|
| OpenCV (`opencv-python`) | Apache-2.0 | video/frame I/O; optional OpenCV 5 `cv.dnn` VLM path |
| NumPy | BSD-3 | |
| Typer / Click / Rich | MIT / BSD-3 / MIT | CLI |
| librosa | ISC | optional — onsets, beats |
| PySceneDetect | BSD-3 | optional — scene detection |
| anthropic | MIT | optional — Claude vision backend |
| OpenTimelineIO | Apache-2.0 | optional — EDL/AAF/OTIO export |
| ffmpeg / ffprobe | LGPL or GPL depending on build | **external binary**, must be on PATH; ship an LGPL build if you bundle it |
| CLAP (LAION) weights | verify per model card | optional — semantic matching; not redistributed |

## Sound-library policy (IMPORTANT)
foley-forge only **bundles or redistributes** audio that is genuinely public-domain/CC0. It integrates other
sources by pointing at files **you** supply.

**Bundle-able (CC0, redistributable):** the built-in synthesized pack, Kenney.nl audio, CC0-filtered
OpenGameArt, and CC0 files you pull from Freesound.

**Usable in your production but NOT bundle-able as a raw library** (the tool will not cache/redistribute
these): Sonniss GDC bundles, Zapsplat, Mixkit, Pixabay Audio — all forbid redistributing the raw files.

**Excluded by default:** BBC Sound Effects (RemArc: non-commercial, revocable), and any Freesound
**CC-BY-NC** result when running a commercial workflow.

**Freesound API:** free for **non-commercial** use only; a commercial product must have each user negotiate
commercial terms with UPF. foley-forge therefore requires **your own** Freesound API key and never ships one.
CC-BY files carry attribution obligations that foley-forge auto-writes into `CREDITS.md`.
