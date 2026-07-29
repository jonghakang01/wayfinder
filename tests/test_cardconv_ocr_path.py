"""OCR is Gemini-only, and a failure says why (강프로 2026-07-28).

The Claude second pass was never reached — Gemini answers first and correctly —
so it sat there untested with a `max_tokens` that would truncate on any current
model and a `content[0]` read that assumes the first block is text. It's gone.
With nothing behind Gemini, swallowing the exception leaves a failed receipt
with nothing to explain it, so the reason goes to stderr.
"""
import importlib
import sys
import types as _types

import pytest

core = importlib.import_module("services._cardconv_core")


@pytest.fixture
def fake_genai(monkeypatch):
    """Stand in for google-genai.

    These tests check our error handling, not Google's SDK, so CI should not
    have to install it — and a test that imports it directly fails on the
    runner while passing locally, which is how it reaches main.
    """
    def install(client_cls):
        google = _types.ModuleType("google")
        genai = _types.ModuleType("google.genai")
        gtypes = _types.ModuleType("google.genai.types")

        class _Part:
            @staticmethod
            def from_bytes(**kw):
                return kw

        gtypes.Part = _Part
        genai.Client = client_cls
        genai.types = gtypes
        google.genai = genai
        monkeypatch.setitem(sys.modules, "google", google)
        monkeypatch.setitem(sys.modules, "google.genai", genai)
        monkeypatch.setitem(sys.modules, "google.genai.types", gtypes)

    return install


def test_no_claude_pass_remains():
    assert not hasattr(core, "_ocr_receipt"), "the Claude OCR pass should be gone"


def test_auto_returns_what_gemini_returned(monkeypatch):
    monkeypatch.setattr(core, "_ocr_receipt_gemini",
                        lambda b, m: [{"amount": 10.0, "_model": "Gemini"}])
    assert core._ocr_receipt_auto(b"x", "image/jpeg") == [{"amount": 10.0, "_model": "Gemini"}]


def test_auto_passes_an_amountless_result_through(monkeypatch):
    """This is the case that used to trigger the Claude retry."""
    monkeypatch.setattr(core, "_ocr_receipt_gemini",
                        lambda b, m: [{"amount": None, "_model": "Gemini"}])
    assert core._ocr_receipt_auto(b"x", "image/jpeg") == [{"amount": None, "_model": "Gemini"}]


def test_a_failed_call_is_empty_and_explains_itself(monkeypatch, capsys, fake_genai):
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    class _Boom:
        def __init__(self, **kw):
            raise RuntimeError("quota exhausted")

    fake_genai(_Boom)
    assert core._ocr_receipt_gemini(b"x", "image/jpeg") == []
    err = capsys.readouterr().err
    assert "gemini failed" in err and "quota exhausted" in err


def test_an_unparseable_reply_is_reported_too(monkeypatch, capsys, fake_genai):
    monkeypatch.setenv("GEMINI_API_KEY", "k")

    class _Resp:
        text = "I'm sorry, I can't read this receipt."

    class _Models:
        def generate_content(self, **kw):
            return _Resp()

    class _Client:
        def __init__(self, **kw):
            self.models = _Models()

    fake_genai(_Client)
    assert core._ocr_receipt_gemini(b"x", "image/jpeg") == []
    assert "no parseable receipt" in capsys.readouterr().err


def test_a_missing_key_is_not_an_error(monkeypatch, capsys):
    """Not configured is a state, not a failure — don't log it on every scan."""
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert core._ocr_receipt_gemini(b"x", "image/jpeg") == []
    assert capsys.readouterr().err == ""
