"""Every app that ships is switchable from Service Control (강프로 2026-08-07).

The list used to be typed by hand in auth.py, so a new app stayed invisible to
the admin screen until someone remembered it — it could be neither granted to
anyone nor switched off. These tests are the thing that remembers.
"""
import services.auth as auth
import server


def test_every_visible_app_is_switchable():
    for path, mod in server.SERVICES.items():
        meta = mod.META
        slug = path.lstrip("/")
        if meta.get("hidden") or slug in auth.UNCONTROLLABLE:
            continue
        assert slug in auth.CONTROLLED_SERVICES, f"{path} is not switchable"
        assert auth.APP_LABELS.get(slug), f"{path} has no label to show an admin"


def test_the_admin_console_is_never_handed_out():
    """Granting it would grant the power to grant."""
    assert "admin" not in auth.CONTROLLED_SERVICES


def test_absorbed_routes_stay_out():
    """/todo and /habit live inside Momentum; offering them separately offers a
    door that is already part of another room."""
    for slug in ("todo", "habit", "dashboard"):
        assert slug not in auth.CONTROLLED_SERVICES


def test_a_brand_new_app_needs_no_edit_here():
    before = set(auth.CONTROLLED_SERVICES)
    try:
        auth.register_services([{"path": "/whatsit", "name": "Whatsit", "icon": "🫧"}])
        assert "whatsit" in auth.CONTROLLED_SERVICES
        assert auth.APP_LABELS["whatsit"] == "🫧 Whatsit"
    finally:
        auth.CONTROLLED_SERVICES.clear()
        auth.CONTROLLED_SERVICES.update(before)
        auth.APP_LABELS.pop("whatsit", None)


def test_registration_never_overwrites_a_curated_label():
    kept = auth.APP_LABELS["cardconv"]
    auth.register_services([{"path": "/cardconv", "name": "Something Else", "icon": "❓"}])
    assert auth.APP_LABELS["cardconv"] == kept


def test_registration_survives_junk():
    """A malformed META must not take the whole registry down with it."""
    before = set(auth.CONTROLLED_SERVICES)
    auth.register_services([{}, {"path": ""}, {"path": "/a/b"}])
    auth.register_services(None)
    assert auth.CONTROLLED_SERVICES == before


def test_timezones_is_there():
    assert "timezones" in auth.CONTROLLED_SERVICES
    assert "Time Zones" in auth.APP_LABELS["timezones"]


# ── the two admin lists must not drift apart (강프로 2026-08-07) ──────────────
# Switching a service on globally is useless if it never appears in the per-user
# checkboxes: the global list knew about Time Zones and the per-user one, which
# was a second hand-written list, did not.

def test_the_per_user_list_is_the_registry():
    import services.admin as admin
    assert admin._visible_services() == sorted(auth.CONTROLLED_SERVICES)


def test_every_switchable_service_has_a_per_user_checkbox(monkeypatch):
    """Rendered markup, not the list behind it — the list agreeing with itself
    is exactly what the bug looked like from the inside.

    The user is seeded rather than borrowed from the machine: the checkboxes
    live in the per-user rows, so on a box with no users this rendered an empty
    table and passed locally while failing in CI, which has none.
    """
    import services.admin as admin
    monkeypatch.setattr(auth, "load_users", lambda: {
        "someone@example.com": {"role": "user", "email": "someone@example.com",
                                "services": []}})
    html = admin.render_admin("__nobody__")
    for slug in auth.CONTROLLED_SERVICES:
        assert f'name="services" value="{slug}"' in html, slug
