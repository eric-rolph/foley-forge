"""The orchestrator: video in, scene narrative + SFX timeline out."""

from __future__ import annotations

from pathlib import Path

from .backends import get_backend
from .config import Config
from .exporters import write_exports
from .ingest import VideoInfo, extract_audio, probe
from .models import AnalysisResult, Cue, SceneObservation, Timeline, TimelineClip
from .sampling import detect_scenes, sample_frames
from .sfx import SFXLibrary, match_event

# Interactions with these labels shouldn't win a cue over a more specific one nearby.
_GENERIC = {"movement", "impact"}
_DEFAULT_SFX_DURATION = 0.5


def load_library(config: Config) -> SFXLibrary:
    lib = SFXLibrary.bundled()
    for folder in config.sfx_libraries:
        if Path(folder).exists():
            lib.extend(SFXLibrary.from_folder(folder))
    return lib


def fuse(
    observations: list[SceneObservation],
    onsets: list[float],
    config: Config,
) -> list[Cue]:
    """Turn per-frame interactions into deduplicated, onset-snapped cues."""
    raw: list[Cue] = []
    for obs in observations:
        for inter in obs.interactions:
            if inter.confidence < config.min_confidence:
                continue
            t_snap, snapped = _snap(obs.t, onsets, config.snap_window)
            raw.append(Cue(
                t=t_snap,
                event=inter.label,
                confidence=inter.confidence,
                source="vlm+onset" if snapped else "vlm",
                description=(inter.raw or obs.description)[:160],
            ))

    raw.sort(key=lambda c: (c.t, -c.confidence))
    merged: list[Cue] = []
    for cue in raw:
        if merged and cue.t - merged[-1].t < config.min_gap:
            prev = merged[-1]
            if _prefer(cue, prev):
                merged[-1] = cue
            continue
        merged.append(cue)
    return merged


def _snap(t: float, onsets: list[float], window: float) -> tuple[float, bool]:
    if not onsets:
        return t, False
    nearest = min(onsets, key=lambda o: abs(o - t))
    if abs(nearest - t) <= window:
        return float(nearest), True
    return t, False


def _prefer(a: Cue, b: Cue) -> bool:
    """Whether cue ``a`` should replace nearby cue ``b``."""
    a_generic, b_generic = a.event in _GENERIC, b.event in _GENERIC
    if a_generic != b_generic:
        return b_generic  # prefer the specific one
    return a.confidence > b.confidence


def build_timeline(info: VideoInfo, cues: list[Cue], config: Config) -> Timeline:
    timeline = Timeline(
        fps=info.fps or 30.0,
        name=Path(info.path).stem + " — foley-forge",
        width=info.width or 1920,
        height=info.height or 1080,
        duration=info.duration or 0.0,
    )
    if config.include_source_video:
        timeline.add(TimelineClip(
            name=Path(info.path).name,
            media_path=info.path,
            start=0.0,
            duration=info.duration or 0.0,
            kind="video",
        ))
    for cue in cues:
        if not cue.sfx:
            continue
        dur = cue.sfx.duration or _DEFAULT_SFX_DURATION
        timeline.add(TimelineClip(
            name=cue.sfx.name,
            media_path=cue.sfx.path,
            start=cue.t,
            duration=dur,
            kind="audio",
            gain_db=cue.gain_db,
            role=config.audio_role,
        ))
    return timeline


def analyze(video_path: str, config: Config, outdir: str | Path) -> AnalysisResult:
    """Run ingest -> scenes -> sample -> caption -> fuse -> match -> timeline."""
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    info = probe(video_path)

    onsets: list[float] = []
    if info.has_audio:
        wav = extract_audio(video_path, str(outdir / "_audio.wav"))
        if wav:
            from .audio import detect_onsets
            onsets = detect_onsets(wav)

    cuts = detect_scenes(video_path, config.scene_threshold) if config.include_cuts else []
    frames = sample_frames(
        info, config.sample_fps, config.max_frames, config.include_cuts, cuts)

    backend = get_backend(config.backend, config.backend_config)
    observations = backend.caption_frames(frames)

    cues = fuse(observations, onsets, config)

    library = load_library(config)
    for cue in cues:
        cue.sfx = match_event(cue.event, library, config.min_score, config.commercial)
        cue.gain_db = config.gain_db

    timeline = build_timeline(info, cues, config)
    result = AnalysisResult(
        video_path=info.path,
        fps=info.fps,
        duration=info.duration,
        width=info.width,
        height=info.height,
        backend=config.backend,
        observations=observations,
        onsets=onsets,
        cues=cues,
        timeline=timeline,
    )
    return result


def run(video_path: str, config: Config, outdir: str | Path) -> dict:
    """Full run: analyze, then write narrative, credits, and timeline exports."""
    from .narrative import write_credits, write_narrative

    outdir = Path(outdir)
    result = analyze(video_path, config, outdir)
    narrative_paths = write_narrative(result, outdir)
    credits_path = write_credits(result, outdir)
    export_paths = write_exports(
        result.timeline, outdir, config.formats,
        include_source_video=config.include_source_video,
        audio_role=config.audio_role,
    )
    placed = sum(1 for c in result.cues if c.sfx)
    return {
        "result": result,
        "narrative": narrative_paths,
        "credits": credits_path,
        "exports": export_paths,
        "cues": len(result.cues),
        "placed": placed,
        "onsets": len(result.onsets),
    }
