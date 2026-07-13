import importlib

MOD = "services.design"


def test_meta_is_valid():
    m = importlib.import_module(MOD).META
    assert m["path"] == "/design"
    assert m["name"] and isinstance(m["name"], str)


def test_get_renders_html():
    mod = importlib.import_module(MOD)
    kind, html = mod.handle("GET", "/design", {}, {"user": "__testuser__"})
    assert kind == "html"
    assert "Design System" in html


def test_page_shows_tokens_and_components():
    mod = importlib.import_module(MOD)
    _, html = mod.handle("GET", "/design", {}, {"user": "__testuser__"})
    assert "--accent" in html and "--on-accent" in html   # token swatches
    assert "ds-stat" in html and "ds-toolbar" in html      # component demos
    assert mod.META.get("admin_only") is True
