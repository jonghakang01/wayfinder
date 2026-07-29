"""Review's SAP-ready set is one click (강프로 2026-07-29).

What goes into the SAP upload is every open transaction that either has its
receipt or has been declared receipt-less. Those lived on two separate stat
cards, and the only card holding both — Open — also holds the ones still
waiting for a receipt, so building the export meant hand-skipping them.
"""
import importlib
import re

render = importlib.import_module("services._cardconv_render")

SRC = open(render.__file__, encoding="utf-8").read()


def test_the_card_exists_and_is_a_view():
    assert 'data-rvview="ready"' in SRC
    assert re.search(r"ready:\s*\{\{view: 'open',\s*matched: 'ready'\}\}", SRC)


def test_the_count_is_the_union():
    """matched and no_rcpt_n are disjoint — no_rcpt_n counts `not matched`."""
    assert "ready_n     = matched + no_rcpt_n" in SRC
    assert 'no_rcpt_n   = sum(1 for e in open_rows if not e.get("matched") and e.get("no_receipt"))' in SRC


def test_the_filter_takes_either_half():
    assert ("rvMatchedF === 'ready' ? (it.dataset.matched === '1' "
            "|| it.dataset.noreceipt === '1')") in SRC


def test_the_ready_view_still_counts_as_open():
    """Export-then-mark-in-progress only offers itself on the open view, and
    the SAP-ready set is exactly what you want that offer on."""
    m = re.search(r"ready:\s*\{\{view: '(\w+)'", SRC)
    assert m and m.group(1) == "open"


def test_the_card_uses_a_token_not_a_hex():
    """A hardcoded colour here would not follow the light theme — and would
    trip the lint ratchet on the way in."""
    card = SRC[SRC.index('data-rvview="ready"'):][:400]
    assert "var(--accent)" in card
    assert not re.search(r"#[0-9a-fA-F]{6}", card)


def test_the_label_is_english():
    card = SRC[SRC.index('data-rvview="ready"'):][:400]
    assert "Ready for SAP" in card
