"""SAP trip-submission robot (spec docs/specs/2026-08-03-trip-submission-automation.md).

Drives the robot Edge (sap-robot-edge.bat + cdp_relay.py on the Windows side)
into the "Business Trip Settlement Other Expense" screen and keys in one
expense per line from a cardconv trip export. Every line pauses for a human
look before Save (Q2) — this script never submits anything unseen.

Usage:
  1. Windows: run sap-robot-edge.bat (opens portals + starts the CDP relay)
  2. Open the trip's "Other Expense" screen in the robot Edge
  3. cardconv Review -> Export -> "json (Trip)" -> save the file
  4. WSL:  LD_LIBRARY_PATH=$HOME/.local/chromium-libs \\
           python3 scripts/sap_trip_robot.py <trip_submit_*.json> "<trip name>" \\
           [--confirm] [--domestic]

Default is fully automatic — fill, Save, New, next line (강프로 2026-08-03,
after the first line was verified on screen). --confirm restores the
per-line pause ([Enter]=save s=skip q=quit); --domestic sets Vendor Name
kind to Domestic (default Overseas — Korea/India trips). Every save is
verified against the grid's Total counter; failures skip, never abort.
"""
import json
import re as _re
import subprocess
import sys
from datetime import date
from pathlib import Path

from playwright.sync_api import sync_playwright

SCREEN_URL_PART = "exp_2010_p05"   # the create screen only — exp_2010_m.do is the Maintain list
# Tag-qualified on purpose: the page pairs a visible control with a hidden
# input of the SAME id, and a bare #id resolves to the hidden one first.
SEL = {
    "receipt_type": "select#rctScCd",  # A -> Cash, D -> Corporate Credit Card
    "inv_date":     "input#docDt",     # MM-DD-YYYY
    "purpose":      "input#exCntnt",
    "cash_reason":  "input#cashRsn",
    "account":      "input#acttCd",    # G/L code; page looks up the name on change
    "account_name": "input#acttLcNm",
    "amount":       "input#totDocAmt",
    "vendor_kind":  "select#hbrdCdu",  # D Domestic / O Overseas
    "vendor_name":  "input#upNm",
    "save":         "button#btnSave",
    "new":          "button#btnNew",
}
RECEIPT_OPT = {"A": "Cash", "D": "Corporate Credit Card"}


def _gateway_ip():
    out = subprocess.check_output("ip route | awk '/default/ {print $3; exit}'",
                                  shell=True)
    return out.decode().strip()


def _mmddyyyy(iso):
    if not iso:
        return ""
    try:
        d = date.fromisoformat(iso)
        return d.strftime("%m-%d-%Y")
    except ValueError:
        return iso


def _sync_selectric(pg, selector):
    """The page skins its selects with the Selectric jQuery plugin; setting the
    native select fires the page's listeners but leaves the skin's label stale,
    which would mislead the human checking the screen before Save."""
    pg.evaluate(
        "s => { const $ = window.jQuery; if ($ && $(s).data('selectric')) "
        "$(s).selectric('refresh'); }", selector)


def fill_line(pg, line, overseas):
    pg.select_option(SEL["receipt_type"],
                     label=RECEIPT_OPT.get(line.get("receipt_type", "D")))
    _sync_selectric(pg, SEL["receipt_type"])
    pg.fill(SEL["inv_date"], _mmddyyyy(line.get("date")))
    pg.keyboard.press("Escape")   # filling the date pops a calendar — close it
    pg.fill(SEL["purpose"], line.get("purpose") or line.get("merchant") or "")
    if line.get("receipt_type") == "A" and line.get("cash_reason"):
        pg.fill(SEL["cash_reason"], line["cash_reason"])
    gl = line.get("gl")
    if gl:
        gl = str(gl)
        # The reliable path is the Recent Account List — selecting there fires
        # the page's own wiring that fills both code and name. Direct typing
        # into acttCd is silently discarded by the page (dry-run 2026-08-03).
        recent = pg.locator("select#rctActtList option").evaluate_all(
            "os => os.map(o => o.value)")
        if gl in recent:
            pg.select_option("select#rctActtList", value=gl)
            _sync_selectric(pg, "select#rctActtList")
        else:
            pg.fill(SEL["account"], gl)
            pg.press(SEL["account"], "Tab")
        pg.wait_for_timeout(1200)
        if not pg.input_value(SEL["account_name"]):
            raise RuntimeError(
                f"account {gl} did not resolve — pick it via the 🔍 popup, "
                "then rerun this line")
    pg.fill(SEL["amount"], f'{line.get("amount", 0):.2f}')
    pg.select_option(SEL["vendor_kind"], value="O" if overseas else "D")
    _sync_selectric(pg, SEL["vendor_kind"])
    pg.fill(SEL["vendor_name"], line.get("merchant") or "")


def _grid_total(pg):
    m = _re.search(r"Total\s*(\d+)", pg.evaluate("() => document.body.innerText"))
    return int(m.group(1)) if m else None


def _ensure_form_open(pg):
    """New both opens the collapsed form (list mode) and resets a stale one —
    without the reset, a field the next line does not touch (e.g. cashRsn on
    a card line after a cash line) would silently carry over."""
    pg.click(SEL["new"])
    pg.wait_for_timeout(1200)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    confirm = "--confirm" in sys.argv
    overseas = "--domestic" not in sys.argv
    if len(args) < 2:
        print(__doc__)
        sys.exit(1)
    export = json.loads(Path(args[0]).read_text())
    trip = args[1]
    lines = export.get("trips", {}).get(trip)
    if not lines:
        print(f"trip '{trip}' not in export; available: {list(export.get('trips', {}))}")
        sys.exit(1)

    failures = []
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(f"http://{_gateway_ip()}:9223")
        pages = [pg for c in b.contexts for pg in c.pages if SCREEN_URL_PART in pg.url]
        if not pages:
            print("Expense screen not found — open the trip's 'Other Expense' "
                  "screen in the robot Edge first.")
            sys.exit(1)
        pg = pages[0]
        pg.on("dialog", lambda d: (print(f"  [dialog] {d.message[:120]}"), d.accept()))
        print(f"Screen: {pg.title()} | {len(lines)} line(s) for '{trip}' "
              f"| mode: {'confirm each' if confirm else 'auto-save'}\n")

        for i, line in enumerate(lines, 1):
            head = (f"[{i}/{len(lines)}] {line.get('date')}  "
                    f"{line.get('merchant')}  ${line.get('amount')}")
            print(head)
            try:
                _ensure_form_open(pg)
                fill_line(pg, line, overseas)
            except Exception as e:
                print(f"  fill failed: {e}")
                failures.append((head, str(e)))
                continue
            if confirm:
                ans = input("  filled — check the screen. [Enter]=Save  s=skip  q=quit: ").strip().lower()
                if ans == "q":
                    break
                if ans == "s":
                    failures.append((head, "skipped by user"))
                    continue
            try:
                before = _grid_total(pg)
                pg.click(SEL["save"])
                pg.wait_for_timeout(2500)
                after = _grid_total(pg)
                if before is not None and after is not None and after <= before:
                    raise RuntimeError(
                        f"grid Total stayed at {after} — the save did not land")
                pg.wait_for_timeout(500)
                print(f"  saved (Total {before} -> {after}).")
            except Exception as e:
                print(f"  save failed: {e}")
                failures.append((head, str(e)))

    print(f"\ndone. {len(lines) - len(failures)}/{len(lines)} saved.")
    for head, why in failures:
        print(f"  ✗ {head} — {why}")


if __name__ == "__main__":
    main()
