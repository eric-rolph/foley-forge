from foley_forge.sfx import SFXLibrary, match_event, normalize_label, tags_for


def test_bundled_library_loads():
    lib = SFXLibrary.bundled()
    assert len(lib) >= 10
    assert all(a.is_cc0 for a in lib.assets)          # bundled pack is all CC0
    assert all(a.duration > 0 for a in lib.assets)


def test_normalize_label():
    assert normalize_label("the door slams shut")[0] == "door_slam"
    assert normalize_label("someone typing on a keyboard")[0] == "keyboard"
    assert normalize_label("a loud gunshot")[0] == "gunshot"
    assert normalize_label("complete gibberish here") == (None, 0.0)


def test_normalize_label_word_boundaries():
    # Short keywords must not fire inside unrelated words.
    assert normalize_label("a scary moment") == (None, 0.0)   # "car" not in "scary"
    assert normalize_label("pushing a cart") == (None, 0.0)   # "car" not in "cart"
    assert normalize_label("the boombox") == (None, 0.0)      # "boom" not in "boombox"


def test_tags_for_unknown_label_uses_tokens():
    assert set(tags_for("metal clang")) == {"metal", "clang"}


def test_match_event_specific():
    lib = SFXLibrary.bundled()
    m = match_event("gunshot", lib)
    assert m is not None
    assert m.asset_id == "boom_low"        # boom_low carries gun/gunshot tags
    assert m.match_type == "lexical"
    assert m.score > 0

    foot = match_event("footstep", lib)
    assert foot.asset_id == "footstep"


def test_match_event_fallback():
    lib = SFXLibrary.bundled()
    m = match_event("teleportation_shimmer", lib)   # no matching tags
    assert m is not None
    assert m.match_type == "fallback"


def test_match_event_empty_library_returns_none():
    assert match_event("impact", SFXLibrary([])) is None
