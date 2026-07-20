import importlib

MOD = "services.notebot"


def test_meta_is_valid():
    m = importlib.import_module(MOD).META
    assert m["path"] == "/notebot"
    assert m["name"] and isinstance(m["name"], str)
    assert m.get("admin_only") is True


def test_get_renders_html():
    mod = importlib.import_module(MOD)
    kind, html = mod.handle("GET", "/notebot", {}, {"user": "__testuser__"})
    assert kind == "html"
    assert "Notebot" in html


def test_state_endpoint_is_json():
    mod = importlib.import_module(MOD)
    if not mod._is_local():
        return  # local-only surface; nothing to assert on prod
    kind, payload = mod.handle("GET", "/notebot/state", {}, {"user": "__testuser__"})
    assert kind == "json"
    assert payload["state"] in ("idle", "recording", "processing")


def test_delete_rejects_bad_sid():
    mod = importlib.import_module(MOD)
    kind, target = mod.handle(
        "POST", "/notebot/delete", {"sid": ["../../etc"]}, {"user": "__testuser__"}
    )
    assert kind in ("redirect", "json")
    if kind == "redirect":
        assert target == "/notebot"


def test_audio_traversal_blocked():
    mod = importlib.import_module(MOD)
    kind, *_ = mod.handle(
        "GET", "/notebot/audio/20260101_0000/../../secret.wav", {}, {"user": "__testuser__"}
    )
    assert kind == "html"  # falls through to 404 or local-only notice
