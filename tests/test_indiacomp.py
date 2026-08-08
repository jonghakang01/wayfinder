"""India Comp — the arithmetic is the product, so it is what the tests pin.

Every money assertion here is a sum that can be done on a calculator, taken
from the spec's acceptance criteria (docs/specs/2026-08-08-indiacomp.md).
"""
import importlib
import shutil
import tempfile

import pytest

MOD = "services.indiacomp"
USER = "__testuser__"


@pytest.fixture
def ic(monkeypatch):
    """A throwaway DATA_ROOT — these tests write, and the real one is a user's."""
    mod = importlib.import_module(MOD)
    d = tempfile.mkdtemp()
    monkeypatch.setattr(mod, "DATA_ROOT", d)
    yield mod
    shutil.rmtree(d, ignore_errors=True)


def test_meta_is_valid():
    m = importlib.import_module(MOD).META
    assert m["path"] == "/indiacomp"
    assert m["name"] and isinstance(m["name"], str)


def test_get_renders_html(ic):
    kind, html = ic.handle("GET", "/indiacomp", {}, {"user": USER})
    assert kind == "html"
    assert "India Comp" in html


# --- the four stages ----------------------------------------------------------

def test_lpa_becomes_rupees_per_year_and_month(ic):
    """24 LPA is ₹2,400,000 a year and ₹200,000 a month (spec)."""
    m = ic.compute(24, 0, 0, 88)
    assert m["offer_yr"] == 2_400_000
    assert m["offer_mo"] == 200_000


def test_spec_worked_example(ic):
    """burden 10%, TP 15%, FX 87.5 → ₹2,640,000 → ₹3,036,000 → $34,697/yr."""
    m = ic.compute(24, 10, 15, 87.5)
    assert m["india_yr"] == 2_640_000
    # approx, not equality: 2,640,000 × 1.15 lands on 3035999.9999999995 in
    # binary floating point. The page prints ₹3,036,000 because display rounds —
    # which is the honest answer, and the reason nothing rounds mid-ladder.
    assert m["us_yr"] == pytest.approx(3_036_000)
    assert round(m["usd_yr"]) == 34_697


def test_default_assumptions_worked_example(ic):
    """The shipped defaults — burden 10%, TP 18%, FX 88 — on the same 24 LPA."""
    m = ic.compute(24, 10, 18, 88)
    assert m["india_yr"] == 2_640_000
    assert round(m["us_yr"]) == 3_115_200
    assert round(m["usd_yr"]) == 35_400
    assert round(m["usd_mo"]) == 2_950


def test_stages_are_multiplied_not_rounded_between(ic):
    """No rounding mid-ladder: the USD figure must match one long calculation."""
    m = ic.compute(23.7, 12.5, 18, 87.35)
    expected = 23.7 * 100_000 * 1.125 * 1.18 / 87.35
    assert m["usd_yr"] == pytest.approx(expected)


def test_zero_fx_falls_back_instead_of_dividing_by_zero(ic):
    m = ic.compute(24, 10, 18, 0)
    assert m["usd_yr"] > 0


# --- candidates ---------------------------------------------------------------

def test_add_and_load_round_trip(ic):
    cid = ic.add(USER, {"name": "A", "lpa": "24"})
    settings, cands = ic.load(USER)
    assert cid and len(cands) == 1
    assert cands[0]["lpa"] == 24
    assert cands[0]["location"] == ic.DEFAULT_LOCATION   # Chennai by default


def test_add_rejects_a_missing_or_zero_offer(ic):
    assert ic.add(USER, {"name": "No offer", "lpa": ""}) is None
    assert ic.add(USER, {"name": "Zero", "lpa": "0"}) is None
    assert ic.load(USER)[1] == []


def test_update_changes_the_offer(ic):
    cid = ic.add(USER, {"name": "A", "lpa": "24"})
    assert ic.update(USER, cid, {"lpa": "30", "name": "A2"})
    c = ic.load(USER)[1][0]
    assert c["lpa"] == 30 and c["name"] == "A2"


def test_delete_removes_only_that_candidate(ic):
    a = ic.add(USER, {"name": "A", "lpa": "24"})
    b = ic.add(USER, {"name": "B", "lpa": "30"})
    assert ic.delete(USER, a)
    left = [c["id"] for c in ic.load(USER)[1]]
    assert left == [b]


def test_ids_do_not_collide_after_a_delete(ic):
    a = ic.add(USER, {"name": "A", "lpa": "24"})
    ic.add(USER, {"name": "B", "lpa": "30"})
    ic.delete(USER, a)
    new = ic.add(USER, {"name": "C", "lpa": "40"})
    ids = [c["id"] for c in ic.load(USER)[1]]
    assert len(set(ids)) == len(ids) and new in ids


# --- assumptions apply to everybody -------------------------------------------

def test_changing_fx_recalculates_every_saved_candidate(ic):
    ic.add(USER, {"name": "A", "lpa": "24"})
    ic.add(USER, {"name": "B", "lpa": "36"})
    settings, cands = ic.load(USER)
    before = [ic.compute_for(c, settings)["usd_yr"] for c in cands]
    ic.save_settings(USER, {"fx_rate": "80"})
    settings, cands = ic.load(USER)
    after = [ic.compute_for(c, settings)["usd_yr"] for c in cands]
    assert all(a > b for a, b in zip(after, before))   # weaker rupee, more USD


def test_changing_tp_recalculates_every_saved_candidate(ic):
    ic.add(USER, {"name": "A", "lpa": "24"})
    ic.save_settings(USER, {"tp_pct": "30"})
    settings, cands = ic.load(USER)
    assert ic.compute_for(cands[0], settings)["us_yr"] == pytest.approx(
        2_640_000 * 1.30)


def test_settings_are_clamped_not_trusted(ic):
    s = ic.save_settings(USER, {"tp_pct": "-5", "fx_rate": "99999999"})
    assert s["tp_pct"] == 0
    assert s["fx_rate"] == ic.LIMITS["fx_rate"][1]


def test_fx_is_stamped_when_the_rate_moves(ic):
    s = ic.save_settings(USER, {"fx_rate": "90"})
    assert s["fx_updated"]
    assert ic.fx_age_days(s) == 0


def test_burden_override_beats_the_shared_assumption(ic):
    ic.add(USER, {"name": "A", "lpa": "24", "burden_override": "20"})
    settings, cands = ic.load(USER)
    assert ic.burden_for(cands[0], settings) == 20
    assert ic.compute_for(cands[0], settings)["india_yr"] == 2_880_000


def test_a_zero_burden_override_survives_as_zero(ic):
    """Blank means "use the shared %"; 0 is a real answer and must not become it."""
    ic.add(USER, {"name": "A", "lpa": "24", "burden_override": "0"})
    settings, cands = ic.load(USER)
    assert ic.burden_for(cands[0], settings) == 0
    assert ic.compute_for(cands[0], settings)["india_yr"] == 2_400_000


def test_blank_override_uses_the_shared_assumption(ic):
    ic.add(USER, {"name": "A", "lpa": "24", "burden_override": ""})
    settings, cands = ic.load(USER)
    assert cands[0]["burden_override"] is None
    assert ic.burden_for(cands[0], settings) == settings["burden_pct"]


# --- the page -----------------------------------------------------------------

def test_empty_state_invites_the_intake(ic):
    html = ic.render(USER)
    assert "No candidates yet" in html
    assert "Add a candidate" in html


def test_page_shows_the_ladder_for_a_saved_candidate(ic):
    ic.add(USER, {"name": "Priya", "role": "Analyst", "lpa": "24"})
    html = ic.render(USER)
    assert "Priya" in html
    assert "₹2,400,000" in html          # step 1
    assert "₹2,640,000" in html          # step 2, burden 10%
    assert "₹3,115,200" in html          # step 3, TP 18%
    assert "$35,400" in html             # step 4, FX 88
    assert 'id="step-4"' in html         # a stat card has somewhere to point


def test_edit_query_opens_the_sheet(ic):
    cid = ic.add(USER, {"name": "Priya", "lpa": "24"})
    html = ic.render(USER, focus=cid, edit=cid)
    assert "wf-modal" in html
    assert "Delete this candidate" in html


def test_post_add_redirects_to_the_new_candidate(ic):
    kind, target = ic.handle("POST", "/indiacomp/add",
                             {"name": ["A"], "lpa": ["24"]}, {"user": USER})
    assert kind == "redirect"
    assert target.startswith("/indiacomp?focus=")


def test_post_add_with_no_offer_still_redirects(ic):
    kind, target = ic.handle("POST", "/indiacomp/add",
                             {"name": ["A"], "lpa": [""]}, {"user": USER})
    assert (kind, target) == ("redirect", "/indiacomp")


def test_a_stale_rate_says_so_on_the_page(ic):
    """The spec's own risk: reviewing against a rate nobody has checked in weeks."""
    settings, cands = ic.load(USER)
    settings["fx_updated"] = "2020-01-01"
    ic.save(USER, settings, cands)
    assert ic.fx_age_days(ic.load(USER)[0]) > ic.FX_STALE_DAYS
    html = ic.render(USER)
    assert "days old" in html and "ic-warn" in html


def test_a_fresh_rate_does_not_warn(ic):
    ic.save_settings(USER, {"fx_rate": "88"})
    assert "days old" not in ic.render(USER)


def test_no_duplicate_element_ids(ic):
    """Three forms carry the same field names. A duplicated id would send the
    edit sheet's labels to the intake's inputs (caught in QA 2026-08-08)."""
    import re
    cid = ic.add(USER, {"name": "Priya", "lpa": "24"})
    html = ic.render(USER, focus=cid, edit=cid)
    ids = re.findall(r'\sid="([^"]+)"', html)
    dupes = {i for i in ids if ids.count(i) > 1}
    assert not dupes, f"duplicate ids: {dupes}"


def test_every_label_points_at_an_input_on_the_page(ic):
    import re
    cid = ic.add(USER, {"name": "Priya", "lpa": "24"})
    html = ic.render(USER, focus=cid, edit=cid)
    ids = set(re.findall(r'\sid="([^"]+)"', html))
    for target in re.findall(r'<label[^>]*\sfor="([^"]+)"', html):
        assert target in ids, f"label for={target} has no input"


def test_html_is_escaped(ic):
    ic.add(USER, {"name": '<script>alert(1)</script>', "lpa": "24"})
    html = ic.render(USER)
    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_a_corrupt_file_falls_back_to_defaults(ic):
    with open(ic._file(USER), "w") as f:
        f.write("{not json")
    settings, cands = ic.load(USER)
    assert settings["tp_pct"] == ic.DEFAULTS["tp_pct"]
    assert cands == []
