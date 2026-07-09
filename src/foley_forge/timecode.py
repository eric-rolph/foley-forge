"""Frame-accurate time <-> timecode conversions for the timeline exporters.

Each NLE interchange format counts time differently:

* **FCP7 XML (xmeml)** uses integer frame indices plus a ``<rate>`` of an integer
  ``timebase`` and an ``ntsc`` flag (e.g. 30 + TRUE == 29.97).
* **FCPXML** uses rational strings ``numerator/denominator + "s"`` on a timescale
  derived from the frame duration (e.g. ``12000/2400s`` == 5.0s at 24 fps).
* **CMX3600 EDL** uses ``HH:MM:SS:FF`` (non-drop) or ``HH:MM:SS;FF`` (drop-frame),
  the frame field counting at the nominal integer rate.

Getting any of these subtly wrong shifts every sound effect off the moment it is
meant to hit, so this module is small, pure, and heavily unit-tested.
"""

from __future__ import annotations

# NTSC fractional rates that most tooling refers to by their rounded name.
_NTSC = {
    23.976: (24, 24000, 1001, False),   # (nominal_int, fcpxml_timebase, fcpxml_framenum, drop)
    23.98: (24, 24000, 1001, False),
    29.97: (30, 30000, 1001, True),
    59.94: (60, 60000, 1001, True),
    119.88: (120, 120000, 1001, True),
}


def _match_ntsc(fps: float) -> tuple[int, int, int, bool] | None:
    # Tolerance must be tighter than the 0.024 gap between 24 and 23.976 so integer
    # rates never collapse onto their NTSC neighbours.
    for nominal_fps, spec in _NTSC.items():
        if abs(fps - nominal_fps) < 0.01:
            return spec
    return None


def normalize_fps(fps: float | str) -> float:
    """Parse an fps that may arrive as a rational string like ``30000/1001``."""
    if isinstance(fps, str):
        fps = fps.strip()
        if "/" in fps:
            num, den = fps.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f else 0.0
        return float(fps)
    return float(fps)


def seconds_to_frames(seconds: float, fps: float) -> int:
    """Actual (sequential) frame index for a wall-clock offset."""
    return int(round(seconds * fps))


def frames_to_seconds(frames: int, fps: float) -> float:
    return frames / fps if fps else 0.0


# --------------------------------------------------------------------------- #
# FCP7 XML (xmeml)
# --------------------------------------------------------------------------- #
def xmeml_rate(fps: float) -> tuple[int, bool]:
    """Return ``(timebase, ntsc)`` for an xmeml ``<rate>`` element."""
    ntsc = _match_ntsc(fps)
    if ntsc:
        return ntsc[0], ntsc[3] or fps != ntsc[0]  # ntsc true for fractional rates
    r = round(fps)
    return r, abs(fps - r) > 0.01


# --------------------------------------------------------------------------- #
# FCPXML
# --------------------------------------------------------------------------- #
def fcpxml_rate(fps: float) -> tuple[int, int]:
    """Return ``(frame_num, timebase)`` such that frameDuration == frame_num/timebase."""
    ntsc = _match_ntsc(fps)
    if ntsc:
        return ntsc[2], ntsc[1]
    exact = {24: (100, 2400), 25: (100, 2500), 30: (100, 3000),
             50: (100, 5000), 60: (100, 6000)}
    r = round(fps)
    if abs(fps - r) < 0.01 and r in exact:
        return exact[r]
    return 100, r * 100


def fcpxml_frame_duration(fps: float) -> str:
    frame_num, timebase = fcpxml_rate(fps)
    return f"{frame_num}/{timebase}s"


def fcpxml_time(seconds: float, fps: float) -> str:
    """Rational FCPXML time string, snapped to the nearest whole frame."""
    frame_num, timebase = fcpxml_rate(fps)
    frame = seconds_to_frames(seconds, fps)
    num = frame * frame_num
    if num == 0:
        return "0s"
    return f"{num}/{timebase}s"


def fcpxml_tc_format(fps: float) -> str:
    ntsc = _match_ntsc(fps)
    return "DF" if (ntsc and ntsc[3]) else "NDF"


# --------------------------------------------------------------------------- #
# CMX3600 EDL
# --------------------------------------------------------------------------- #
def edl_rate(fps: float) -> tuple[int, bool]:
    """Return ``(nominal_fps, drop_frame)`` for EDL timecode."""
    ntsc = _match_ntsc(fps)
    if ntsc:
        return ntsc[0], ntsc[3]
    r = round(fps)
    return r, False


def _frames_to_hmsf(frame_number: int, fps_int: int, drop: bool) -> tuple[int, int, int, int]:
    """Convert a sequential frame index to (h, m, s, f), honoring drop-frame.

    Drop-frame is defined only for 29.97 (fps_int 30) and 59.94 (fps_int 60);
    it renumbers labels (dropping 2 or 4 per minute, except every tenth minute)
    so the timecode tracks wall-clock time. Standard algorithm.
    """
    if frame_number < 0:
        frame_number = 0
    if drop and fps_int in (30, 60):
        drop_frames = 2 if fps_int == 30 else 4
        frames_per_24h = fps_int * 3600 * 24
        # round(actual_fps * 600): 30*600 - 2*9 == 17982 == round(29.97 * 600).
        frames_per_10m = fps_int * 600 - drop_frames * 9
        frames_per_min = fps_int * 60 - drop_frames

        frame_number %= frames_per_24h
        d = frame_number // frames_per_10m
        m = frame_number % frames_per_10m
        if m > drop_frames:
            frame_number += (drop_frames * 9 * d) + drop_frames * ((m - drop_frames) // frames_per_min)
        else:
            frame_number += drop_frames * 9 * d

    fr = frame_number % fps_int
    sec = (frame_number // fps_int) % 60
    mins = (frame_number // (fps_int * 60)) % 60
    hrs = (frame_number // (fps_int * 3600)) % 24
    return hrs, mins, sec, fr


def edl_timecode(seconds: float, fps: float) -> str:
    """``HH:MM:SS:FF`` (non-drop) or ``HH:MM:SS;FF`` (drop-frame)."""
    nominal, drop = edl_rate(fps)
    total = seconds_to_frames(seconds, fps)
    hrs, mins, sec, fr = _frames_to_hmsf(total, nominal, drop)
    sep = ";" if drop else ":"
    return f"{hrs:02d}:{mins:02d}:{sec:02d}{sep}{fr:02d}"
