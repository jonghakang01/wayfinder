import importlib
import os

MOD = "services.toast"


def _mod():
    return importlib.import_module(MOD)


def test_meta_is_valid():
    m = _mod().META
    assert m["path"] == "/toast"
    assert m["name"] and isinstance(m["name"], str)


def test_get_renders_app_html():
    kind, html = _mod().handle("GET", "/toast", {}, {"user": "__testuser__"})
    assert kind == "html"
    assert "술자리 컴패니언" in html
    assert "/toast/api/preload" in html  # API paths rewritten for webapp


def test_canon_asset_is_sound():
    kind, data = _mod().handle("GET", "/toast/api/canon", {}, {"user": "__testuser__"})
    assert kind == "json"
    items = data["items"]
    assert len(items) >= 100
    for e in items:
        assert e["call"] and e["resp"] and e["expl"]
        assert e["fresh"] in ("스테디", "요즘", "한물", "주의")
        assert 1 <= e["pop"] <= 3


def test_preload_falls_back_to_shipped_collection(tmp_path, monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "_cache_path", lambda: str(tmp_path / "none.json"))
    kind, data = mod.handle("POST", "/toast/api/preload", {"occasion": ["환영"]}, {})
    assert kind == "json"
    assert data["src"] == "collection"
    assert len(data["toasts"]) >= 8


def test_valid_toast_filter_bounds():
    v = _mod()._valid_toast
    assert v({"lang": "ko", "response_word": "위하여"})
    assert v({"lang": "ko", "response_word": "고"})
    assert not v({"lang": "ko", "response_word": "감사합니다"})
    assert v({"lang": "en", "response_word": "Together forever"})


def test_generate_is_lazy_about_sdk():
    # importing the module must not require the anthropic package
    src = open(os.path.join(os.path.dirname(_mod().__file__), "toast.py")).read()
    head = src.split("def generate")[0]
    assert "import anthropic" not in head


def test_prompts_asset_complete():
    p = _mod()._asset_json("prompts.json")
    assert p["system"]
    assert set(p["mix_plans"]) == {"all_korean", "mixed", "mostly_english"}
    for k in ("occasion", "crowd", "age", "role", "mix", "tone", "round", "orgs", "scene", "ask"):
        assert k in p["user_lines"]
