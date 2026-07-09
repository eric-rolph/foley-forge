# 🎬 foley-forge

**Auto-foley for video editors.** Point it at a video, and foley-forge watches the footage, writes a
timestamped *scene narrative*, detects on-screen **physical interactions** (a door slam, a punch, footsteps,
a glass breaking, a keyboard clack), matches each one to a **sound effect**, and drops the SFX onto a
**video-editor timeline** you import straight into DaVinci Resolve, Premiere Pro, or Final Cut.

No manual scrubbing for "where does the *whoosh* go." foley-forge finds the moment, snaps it to the exact
audio transient, picks a sound, and hands you an editable timeline — you keep final say on every cue.

```
video (any container) ──► scene narrative + detected interactions ──► matched SFX ──► drop.xml / drop.fcpxml / drop.edl
```

---

## Why this exists (and an honest note on "OpenCV 5 VLM")

OpenCV **5.0** (June 2026) really did add on-device LLM/VLM *execution* inside `cv::dnn` (new graph engine,
`cv.dnn.Tokenizer`, opt-in KV-cache). But as of 5.0 it is **not** a turnkey captioning API — there is no
`net.caption(image)`. The only reference VLM is **PaliGemma2-3B**, run as a hand-assembled 3-graph ONNX
pipeline, **CPU-only**, without a VLM KV-cache. That is a promising 1.0 capability, not something a shipping
tool should depend on for fast, many-frame captioning.

So foley-forge is **backend-pluggable**:

* it uses **OpenCV** for what OpenCV is genuinely excellent at — decoding, frame I/O, resizing, scene diffing;
* and it sends frames to a **caption backend** you choose — a local OpenAI-compatible server
  (llama.cpp / Ollama / LM Studio / vLLM), the Anthropic cloud, or the **experimental** OpenCV 5 `cv.dnn`
  path — plus a **zero-dependency heuristic backend** so the whole tool runs and produces a timeline with no
  model download and no GPU.

You get an honest tool that is fast today and ready for OpenCV 5.1+ when its VLM path matures.

---

## Quickstart

```bash
# from source (recommended while it's young)
git clone https://github.com/eric-rolph/foley-forge
cd foley-forge
python -m venv .venv && . .venv/Scripts/activate   # Windows;  use .venv/bin/activate on macOS/Linux
pip install -e ".[audio,scenes]"

# needs ffmpeg on PATH (https://ffmpeg.org)  — check with:  ffmpeg -version

# analyze a clip with the offline heuristic backend (no model needed):
foley-forge analyze myclip.mp4 -o out/

# open out/drop.xml in DaVinci Resolve / Premiere, or out/drop.fcpxml in Final Cut.
# read out/scene_narrative.md to see what it detected and why.
```

Use a real vision model for content-aware detection:

```bash
# point at any OpenAI-compatible vision server (llama.cpp --server, Ollama, LM Studio, vLLM):
foley-forge analyze myclip.mp4 --backend openai \
    --base-url http://localhost:8080/v1 --model qwen2.5-vl-7b-instruct -o out/

# or the Anthropic cloud (pip install ".[cloud]", set ANTHROPIC_API_KEY):
foley-forge analyze myclip.mp4 --backend anthropic --model claude-sonnet-5 -o out/
```

---

## How it works

| Stage | What happens | Built on |
|-------|--------------|----------|
| **Ingest** | Probe fps/duration, extract a 16 kHz mono WAV | `ffprobe` / `ffmpeg` |
| **Scenes** | Shot/scene cut boundaries | PySceneDetect *(optional)* → frame-diff fallback |
| **Sample** | Adaptive frame sampling + one frame per cut | OpenCV `VideoCapture` |
| **Caption ("what")** | Per-frame scene description + structured interactions | pluggable VLM backend |
| **Onsets ("when")** | Precise audio transients so the SFX lands on the *hit* | librosa *(optional)* → numpy flux fallback |
| **Fuse** | Snap each interaction to the nearest transient; dedup | — |
| **Match** | Event label → SFX file (tag lexical; CLAP semantic *planned*) | AudioSet-style taxonomy |
| **Export** | Place cues on a timeline the NLE imports | hand-rolled FCPXML / FCP7 XML / EDL |

Outputs written to `-o/--out`:

* `scene_narrative.md` / `.json` — timestamped narration + every detected interaction and chosen cue
* `drop.xml` — **FCP7 XML (xmeml)**: the one format **both DaVinci Resolve and Premiere Pro** import
* `drop.fcpxml` — **FCPXML v1.9**: for **Final Cut Pro** (and Resolve)
* `drop.edl` — **CMX3600 EDL**: lossy universal fallback
* `CREDITS.md` — license/attribution provenance for every sound used

> **No single interchange imports everywhere.** Premiere reads xmeml but *not* FCPXML; Final Cut reads FCPXML
> but *not* xmeml. foley-forge emits both plus an EDL so you pick the one your NLE wants.

---

## Caption backends

| `--backend` | What it is | Needs |
|-------------|-----------|-------|
| `mock` *(default)* | Heuristic: frame-difference motion + audio onsets → generic impact/whoosh cues. **Runs offline, no model, no GPU.** | nothing |
| `openai` | Any OpenAI-compatible `/v1/chat/completions` vision server (llama.cpp, Ollama, LM Studio, vLLM) | a running server |
| `anthropic` | Claude vision (cloud) | `pip install ".[cloud]"`, `ANTHROPIC_API_KEY` |
| `opencv5` | **Experimental.** PaliGemma2-3B via OpenCV 5 `cv.dnn` `ENGINE_NEW` | OpenCV 5 + exported ONNX graphs |

Recommended local model: a small quantized VLM such as **Qwen2.5-VL-7B**, **MiniCPM-V 2.6**, or **Moondream2**
served with GGUF + mmproj via llama.cpp, or `ollama run qwen2.5-vl`.

---

## Sound library & licensing (read this before you monetize)

foley-forge ships a tiny **CC0** starter pack (original, procedurally-synthesized sounds — genuinely
public-domain and redistributable). To go beyond it:

* **Bring your own packs.** Point `foley-forge index-sfx <dir>` at any folder of `.wav`/`.mp3`. Truly
  bundle-able free sources include **Kenney.nl** (CC0) and CC0-filtered **OpenGameArt**.
* **Freesound (bring-your-own API key).** `pip install ".[freesound]"` exposes a Python helper
  (`foley_forge.sfx.freesound.FreesoundClient`) to search **CC0 / CC-BY** sounds and download previews with
  your own token — there's no one-command import yet. Bring the files in with `index-sfx` (set correct
  per-file `license`/`author` in the manifest). `CREDITS.md` is then auto-written for any non-CC0 sound
  actually placed on a timeline, and CC-BY-NC is excluded from commercial runs by default.

⚠️ **Do not bundle** Sonniss GDC, Zapsplat, Mixkit, Pixabay, or BBC Sound Effects — all permit use *inside
your own production* but **forbid redistributing the raw files** as a library (BBC is also non-commercial and
revocable). foley-forge will never cache those into a shareable pack. See [`NOTICE.md`](NOTICE.md).

---

## Roadmap

The core is video → SFX. The highest-synergy additions (each with a mature OSS building block) are in
[`ROADMAP.md`](ROADMAP.md): loudness normalization + auto-ducking, scene-cue transitions, captions/subtitles,
silence trimming & jump-cuts, and beat-synced SFX.

## Status

**v0.1 — alpha.** The full pipeline runs end-to-end offline via the `mock` backend and emits valid
xmeml/FCPXML/EDL. Real VLM backends work against a configured server. See [`CHANGELOG.md`](CHANGELOG.md).

## License

MIT (code). Bundled sounds CC0. Third-party dependency notices in [`NOTICE.md`](NOTICE.md).
