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


def test_state_roundtrip_and_isolation(tmp_path, monkeypatch):
    mod = _mod()
    monkeypatch.setattr(
        mod, "_state_path",
        lambda user: str(tmp_path / f"{user}.json"))
    kind, empty = mod.handle("GET", "/toast/api/state", {}, {"user": "a"})
    assert (kind, empty) == ("json", {})
    blob = {"state": {"occasion": ["환영"], "occasion_note": "첫 합류"},
            "events": [{"id": "e1"}], "persons": [], "saved": [], "active": "e1"}
    kind, out = mod.handle("POST", "/toast/api/state", blob, {"user": "a"})
    assert out["ok"] and out["updated_at"]
    kind, back = mod.handle("GET", "/toast/api/state", {}, {"user": "a"})
    assert back["state"]["occasion_note"] == "첫 합류"
    assert back["active"] == "e1"
    kind, other = mod.handle("GET", "/toast/api/state", {}, {"user": "b"})
    assert other == {}  # per-account isolation


def test_state_rejects_non_dict(tmp_path, monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "_state_path", lambda user: str(tmp_path / "x.json"))
    kind, out = mod.handle("POST", "/toast/api/state", "junk", {"user": "a"})
    assert out.get("error")


def test_occasion_note_partitions_preload_cache():
    ck = _mod().cache_key
    base = {"occasion": ["환영"], "tone": "무난"}
    assert ck(base) != ck({**base, "occasion_note": "재계약 기념"})


def test_news_uses_cache_within_ttl_and_stale_fallback(tmp_path, monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "_news_cache_path", lambda: str(tmp_path / "news.json"))
    calls = {"fetch": 0, "sum": 0}

    def fake_fetch(q, hl="ko", gl="KR", limit=10):
        calls["fetch"] += 1
        return [{"title": "삼성, 신제품 발표", "link": "http://x", "date": "", "source": "s"}]

    def fake_sum(label, items):
        calls["sum"] += 1
        return {"headline": "h", "points": [{"point": "p", "why": "w"}]}

    monkeypatch.setattr(mod, "fetch_headlines", fake_fetch)
    monkeypatch.setattr(mod, "summarize_headlines", fake_sum)
    first = mod.news_get("삼성전자", "ko", "KR")
    assert first["summary"]["headline"] == "h" and calls["sum"] == 1
    again = mod.news_get("삼성전자", "ko", "KR")
    assert again.get("cached") and calls["sum"] == 1  # TTL hit, no re-summary
    forced = mod.news_get("삼성전자", "ko", "KR", max_age=0)
    assert calls["sum"] == 2 and "cached" not in forced

    def boom(q, hl="ko", gl="KR", limit=10):
        raise RuntimeError("network down")
    monkeypatch.setattr(mod, "fetch_headlines", boom)
    stale = mod.news_get("삼성전자", "ko", "KR", max_age=0)
    assert stale.get("stale") and stale["summary"]["headline"] == "h"
    miss = mod.news_get("한국타이어", "ko", "KR")
    assert miss.get("error")


def test_news_route_reads_query_params(tmp_path, monkeypatch):
    mod = _mod()
    monkeypatch.setattr(mod, "_news_cache_path", lambda: str(tmp_path / "news.json"))
    seen = {}

    def fake_get(q, hl, gl, label="", max_age=None):
        seen.update(q=q, hl=hl, gl=gl, label=label, max_age=max_age)
        return {"ok": True}

    monkeypatch.setattr(mod, "news_get", fake_get)
    query = {"q": ["Samsung"], "hl": ["en-US"], "gl": ["US"],
             "label": ["삼성 US"], "mode": ["warm"]}
    kind, out = mod.handle("GET", "/toast/api/news", query, {"user": "a"})
    assert out == {"ok": True}
    assert seen == {"q": "Samsung", "hl": "en-US", "gl": "US",
                    "label": "삼성 US", "max_age": mod.NEWS_WARM_TTL}
    kind, out = mod.handle("GET", "/toast/api/news", {}, {"user": "a"})
    assert out.get("error")


def test_news_rss_parser_is_lenient():
    xml = b"""<?xml version="1.0"?><rss><channel>
      <item><title>T1</title><link>http://a</link><pubDate>Fri, 01 Aug 2026 09:00:00 GMT</pubDate><source url="http://s">S1</source></item>
      <item><title></title></item>
      <item><title>T2</title></item>
    </channel></rss>"""
    mod = _mod()

    class FakeResp:
        def read(self):
            return xml
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    import urllib.request
    orig = urllib.request.urlopen
    urllib.request.urlopen = lambda req, timeout=10: FakeResp()
    try:
        items = mod.fetch_headlines("q", "en-US", "US")
    finally:
        urllib.request.urlopen = orig
    assert [i["title"] for i in items] == ["T1", "T2"]
    assert items[0]["link"] == "http://a" and items[0]["source"] == "S1"


def test_generate_is_lazy_about_sdk():
    # importing the module must not require the anthropic package:
    # every SDK import must live inside a function body (indented)
    src = open(os.path.join(os.path.dirname(_mod().__file__), "toast.py")).read()
    sdk_imports = [ln for ln in src.splitlines() if "import anthropic" in ln]
    assert sdk_imports and all(ln.startswith("    ") for ln in sdk_imports)


def test_prompts_asset_complete():
    p = _mod()._asset_json("prompts.json")
    assert p["system"]
    assert set(p["mix_plans"]) == {"all_korean", "mixed", "mostly_english"}
    for k in ("occasion", "crowd", "age", "role", "mix", "tone", "round", "orgs", "scene", "ask"):
        assert k in p["user_lines"]
