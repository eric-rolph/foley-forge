import xml.etree.ElementTree as ET

from foley_forge.exporters import export_edl, export_fcp7xml, export_fcpxml


def _parse(xml_str: str) -> ET.Element:
    lines = [
        ln for ln in xml_str.splitlines()
        if not ln.startswith("<?xml") and not ln.startswith("<!DOCTYPE")
    ]
    return ET.fromstring("\n".join(lines))


def test_fcp7xml_structure(simple_timeline):
    xml = export_fcp7xml(simple_timeline)
    assert xml.startswith("<?xml")
    assert "<!DOCTYPE xmeml>" in xml
    root = _parse(xml)
    assert root.tag == "xmeml"
    assert root.get("version") == "5"

    rate = root.find("./sequence/rate")
    assert rate.findtext("timebase") == "30"
    assert rate.findtext("ntsc") == "FALSE"

    audio_items = root.findall("./sequence/media/audio/track/clipitem")
    assert len(audio_items) == 3

    whoosh = next(c for c in audio_items if c.findtext("name") == "whoosh")
    assert whoosh.findtext("start") == "30"   # 1.0s @ 30fps
    assert whoosh.findtext("end") == "45"     # +0.5s = 15 frames
    assert whoosh.find("file/pathurl").text.startswith("file://localhost")

    # Overlapping whoosh (1.0-1.5) and impact (1.2-1.7) must land on separate tracks.
    tracks = root.findall("./sequence/media/audio/track")
    assert len(tracks) >= 2


def test_fcpxml_structure(simple_timeline):
    xml = export_fcpxml(simple_timeline)
    assert "<!DOCTYPE fcpxml>" in xml
    root = _parse(xml)
    assert root.tag == "fcpxml"
    assert root.get("version") == "1.9"

    fmt = root.find("./resources/format")
    assert fmt.get("frameDuration") == "100/3000s"

    sfx = [c for c in root.iter("asset-clip") if c.get("lane")]
    assert len(sfx) == 3
    whoosh = next(c for c in sfx if c.get("name") == "whoosh")
    assert whoosh.get("offset") == "3000/3000s"     # 1.0s @ 30fps
    assert int(whoosh.get("lane")) < 0

    asset = root.find("./resources/asset[@hasAudio='1']")
    assert asset.find("media-rep").get("src").startswith("file:///")


def test_edl_structure(simple_timeline):
    edl = export_edl(simple_timeline)
    lines = edl.splitlines()
    assert lines[0] == "TITLE: foley-forge"
    assert lines[1] == "FCM: NON-DROP FRAME"
    events = [ln for ln in lines if ln[:3].isdigit()]
    assert len(events) == 3
    assert any("00:00:01:00" in ln for ln in events)      # whoosh rec-in
    assert edl.count("* FROM CLIP NAME:") == 3
    # Overlapping whoosh (1.0-1.5) and impact (1.2-1.7) must land on different channels.
    channels = [ln.split()[2] for ln in events]
    assert channels[0] == "A"          # first event on audio channel 1
    assert set(channels) == {"A", "A2"}
