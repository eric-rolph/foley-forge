"""foley-forge command-line interface."""

from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.markup import escape
from rich.table import Table

from . import __version__
from .backends import list_backends
from .config import Config

app = typer.Typer(
    add_completion=False,
    help="Auto-foley for editors: detect on-screen interactions and drop SFX onto a timeline.",
)
console = Console()


@app.command()
def analyze(
    video: Path = typer.Argument(..., exists=True, dir_okay=False, help="Input video (any container)."),
    out: Path = typer.Option(Path("out"), "--out", "-o", help="Output directory."),
    backend: str | None = typer.Option(None, "--backend", "-b", help="mock | openai | anthropic | opencv5"),
    config: Path | None = typer.Option(None, "--config", "-c", help="TOML config file."),
    base_url: str | None = typer.Option(None, "--base-url", help="OpenAI-compatible server URL."),
    model: str | None = typer.Option(None, "--model", help="Model name for openai/anthropic backend."),
    api_key: str | None = typer.Option(None, "--api-key", help="API key (or use env vars)."),
    sample_fps: float | None = typer.Option(None, "--sample-fps", help="Frames/sec to caption."),
    formats: str | None = typer.Option(None, "--formats", help="Comma list: fcp7xml,fcpxml,edl,otio"),
    commercial: bool = typer.Option(True, "--commercial/--non-commercial",
                                    help="Exclude CC-BY-NC sounds (commercial default)."),
    source_video: bool = typer.Option(True, "--source-video/--no-source-video",
                                      help="Place the source clip on the timeline."),
):
    """Analyze VIDEO and write a scene narrative + SFX timeline into OUT."""
    from .ingest import FFmpegNotFound
    from .pipeline import run

    cfg = Config.load(config)
    if backend:
        cfg.backend = backend
    if sample_fps is not None:
        cfg.sample_fps = sample_fps
    if formats:
        cfg.formats = [f.strip() for f in formats.split(",") if f.strip()]
    cfg.commercial = commercial
    cfg.include_source_video = source_video

    # Backend connection overrides.
    if base_url:
        cfg.backend_config["base_url"] = base_url
    if model:
        cfg.backend_config["model"] = model
    if api_key:
        cfg.backend_config["api_key"] = api_key

    console.print(f"[bold]foley-forge[/] · backend=[cyan]{cfg.backend}[/] · {video.name}")
    try:
        summary = run(str(video), cfg, out)
    except FFmpegNotFound as e:
        console.print(f"[red]ffmpeg error:[/] {e}")
        raise typer.Exit(code=2) from e

    _print_summary(summary, out)


def _print_summary(summary: dict, out: Path) -> None:
    result = summary["result"]
    console.print(
        f"\n[green]done[/] {summary['placed']}/{summary['cues']} cues placed "
        f"- {summary['onsets']} onsets - {result.duration:.1f}s @ {result.fps:.2f}fps"
    )
    table = Table(title="Timeline exports", show_header=True, header_style="bold")
    table.add_column("Format")
    table.add_column("File")
    for fmt, path in summary["exports"].items():
        table.add_row(fmt, str(path))
    table.add_row("narrative", str(summary["narrative"]["markdown"]))
    table.add_row("credits", str(summary["credits"]))
    console.print(table)
    console.print(f"\nOpen [bold]{out / 'drop.xml'}[/] in DaVinci Resolve / Premiere, "
                  f"or [bold]{out / 'drop.fcpxml'}[/] in Final Cut.")


@app.command()
def backends():
    """List caption backends and whether each can run right now."""
    table = Table(title="Caption backends", header_style="bold")
    table.add_column("Name")
    table.add_column("Available")
    table.add_column("Description")
    for name, available, desc in list_backends():
        mark = "[green]yes[/]" if available else "[yellow]no[/]"
        table.add_row(name, mark, escape(desc))
    console.print(table)


@app.command("index-sfx")
def index_sfx(
    folder: Path = typer.Argument(..., exists=True, file_okay=False, help="Folder of audio files."),
    out: Path = typer.Option(Path("sfx_manifest.json"), "--out", "-o", help="Manifest output path."),
    license: str = typer.Option("CC0-1.0", "--license", help="License to record for these files."),
):
    """Build an SFX manifest from a folder (tags derived from filenames)."""
    from .sfx import SFXLibrary

    lib = SFXLibrary.from_folder(folder, license=license)
    out.write_text(json.dumps(lib.to_manifest(), indent=2), encoding="utf-8")
    console.print(f"[green]done[/] indexed {len(lib)} sounds -> {out}")


@app.command()
def version():
    """Print the foley-forge version."""
    console.print(f"foley-forge {__version__}")


if __name__ == "__main__":  # pragma: no cover
    app()
