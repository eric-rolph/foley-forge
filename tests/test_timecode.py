from foley_forge import timecode as tc


def test_frame_roundtrip():
    assert tc.seconds_to_frames(5.0, 24) == 120
    assert tc.seconds_to_frames(1.0, 29.97) == 30  # round(29.97) == 30
    assert abs(tc.frames_to_seconds(120, 24) - 5.0) < 1e-9


def test_xmeml_rate():
    assert tc.xmeml_rate(30) == (30, False)
    assert tc.xmeml_rate(29.97) == (30, True)
    assert tc.xmeml_rate(24) == (24, False)
    assert tc.xmeml_rate(23.976) == (24, True)
    assert tc.xmeml_rate(25) == (25, False)


def test_fcpxml_rate_and_duration():
    assert tc.fcpxml_rate(24) == (100, 2400)
    assert tc.fcpxml_rate(30) == (100, 3000)
    assert tc.fcpxml_rate(29.97) == (1001, 30000)
    assert tc.fcpxml_frame_duration(24) == "100/2400s"
    assert tc.fcpxml_frame_duration(29.97) == "1001/30000s"


def test_fcpxml_time():
    assert tc.fcpxml_time(0.0, 24) == "0s"
    assert tc.fcpxml_time(5.0, 24) == "12000/2400s"       # 120 frames * 100
    assert tc.fcpxml_time(1.0, 29.97) == "30030/30000s"   # 30 frames * 1001
    assert tc.fcpxml_tc_format(29.97) == "DF"
    assert tc.fcpxml_tc_format(30) == "NDF"
    assert tc.fcpxml_tc_format(23.976) == "NDF"


def test_edl_rate():
    assert tc.edl_rate(29.97) == (30, True)
    assert tc.edl_rate(30) == (30, False)
    assert tc.edl_rate(23.976) == (24, False)


def test_edl_timecode_nondrop():
    assert tc.edl_timecode(0.0, 30) == "00:00:00:00"
    assert tc.edl_timecode(1.0, 30) == "00:00:01:00"
    assert tc.edl_timecode(3.0, 30) == "00:00:03:00"
    assert tc.edl_timecode(1.0, 25) == "00:00:01:00"
    assert tc.edl_timecode(61.5, 30) == "00:01:01:15"


def test_edl_timecode_dropframe():
    # Drop-frame uses ';' and follows the standard Heidelberger renumbering.
    assert tc.edl_timecode(0.0, 29.97) == "00:00:00;00"
    # Frame 1800 (first frame of minute 1) is labeled ;02 (00 and 01 dropped).
    assert tc._frames_to_hmsf(1800, 30, True) == (0, 1, 0, 2)
    # Frame 1799 (last of minute 0) is still 00:00:59;29.
    assert tc._frames_to_hmsf(1799, 30, True) == (0, 0, 59, 29)
    # DF realigns with real time every 10 minutes: actual frame 17982 -> 00:10:00;00.
    assert tc._frames_to_hmsf(17982, 30, True) == (0, 10, 0, 0)
