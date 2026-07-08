"""FX conversion for foreign-currency receipts (KRW/INR → USD band matching)."""
import importlib

core = importlib.import_module("services._cardconv_core")


def test_coerce_currency():
    f = core._coerce_currency
    assert f("KRW") == "KRW"
    assert f("krw") == "KRW"
    assert f("₩") == "KRW"
    assert f("원") == "KRW"
    assert f("Rs") == "INR"
    assert f("₹") == "INR"
    assert f("USD") == "USD"
    assert f("$") == "USD"
    assert f(None) is None
    assert f("null") is None
    assert f("won?!") is None  # not a 3-letter alpha code


def test_usd_estimate_uses_rate(monkeypatch):
    monkeypatch.setattr(core, "_fx_rate", lambda cur, d=None: 1390.0)
    usd, rate = core._fx_usd_estimate(45000, "KRW", "2026-07-01")
    assert rate == 1390.0
    assert usd == round(45000 / 1390.0, 2)


def test_usd_estimate_usd_passthrough():
    assert core._fx_usd_estimate(33.10, "USD") == (None, None)
    assert core._fx_usd_estimate(None, "KRW") == (None, None)


def test_fx_rate_offline_fallback(monkeypatch, tmp_path):
    # Network down → static fallback keeps matching functional offline.
    import urllib.request

    def boom(*a, **k):
        raise OSError("offline")

    monkeypatch.setattr(urllib.request, "urlopen", boom)
    monkeypatch.setattr(core, "_FX_CACHE_FILE", tmp_path / "fx.json")
    assert core._fx_rate("KRW") == core._FX_FALLBACK["KRW"]
    assert core._fx_rate("INR") == core._FX_FALLBACK["INR"]
    assert core._fx_rate("XXX") is None
    assert core._fx_rate("USD") == 1.0


def test_band_matching_logic():
    # ±5% band: ECB estimate $32.37 should match card-settled $33.10 (2.2% off)
    usd_est = 32.37
    assert abs(33.10 - usd_est) <= usd_est * core.FX_TOLERANCE
    # but not a wildly different amount
    assert abs(45.00 - usd_est) > usd_est * core.FX_TOLERANCE
