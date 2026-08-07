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


# ── the two halves of the admin screen are one flow (강프로 2026-08-07) ───────
# Global Service Control decides what is in service at all; only those apps
# appear in each user's checkboxes to be handed out person by person. The two
# lists drifting apart — one hand-written, one not — is the morning's bug.

def _seed(monkeypatch, on, users=None):
    monkeypatch.setattr(auth, "load_settings",
                        lambda: {"available_services": list(on)})
    monkeypatch.setattr(auth, "load_users", lambda: users if users is not None
                        else {"someone@example.com":
                              {"role": "user", "email": "someone@example.com",
                               "services": []}})


def test_the_per_user_list_is_the_registry_filtered_by_the_switches(monkeypatch):
    import services.admin as admin
    _seed(monkeypatch, on=["cardconv", "timezones", "not-a-real-app"])
    assert admin._visible_services() == ["cardconv", "timezones"]


def test_every_switched_on_service_has_a_per_user_checkbox(monkeypatch):
    """Rendered markup, not the list behind it — the list agreeing with itself
    is exactly what the bug looked like from the inside.

    The user and the settings are both seeded rather than borrowed from the
    machine: the checkboxes live in per-user rows, so a box with no users
    rendered an empty table and passed locally while failing in CI.
    """
    import services.admin as admin
    _seed(monkeypatch, on=sorted(auth.CONTROLLED_SERVICES))
    html = admin.render_admin("__nobody__")
    for slug in auth.CONTROLLED_SERVICES:
        assert f'name="services" value="{slug}"' in html, slug


def test_a_switched_off_service_offers_no_checkbox(monkeypatch):
    """Offering it would grant access to something the switch says is off."""
    import services.admin as admin
    _seed(monkeypatch, on=["cardconv"])
    html = admin.render_admin("__nobody__")
    assert 'name="services" value="cardconv"' in html
    assert 'name="services" value="timezones"' not in html


def test_a_grant_for_a_switched_off_service_survives_and_is_named(monkeypatch):
    """Switching an app off hides its checkbox but revokes nobody — and the
    grant is shown as dormant rather than silently vanishing from the screen."""
    import services.admin as admin
    _seed(monkeypatch, on=["cardconv"],
          users={"someone@example.com":
                 {"role": "user", "email": "someone@example.com",
                  "services": ["cardconv", "timezones"]}})
    html = admin.render_admin("__nobody__")
    assert "💤" in html and "Time Zones" in html      # named as dormant
    # and the save form's scope excludes it, so saving cannot revoke it
    assert 'name="scope" value="cardconv"' in html


def test_saving_within_scope_leaves_off_list_grants_alone(monkeypatch):
    """The scope field is what makes the survival real, not just cosmetic:
    set_services only rewrites grants inside the scope it was shown."""
    import services.admin as admin
    store = {"someone@example.com":
             {"role": "user", "email": "someone@example.com",
              "services": ["cardconv", "timezones"]}}
    monkeypatch.setattr(auth, "load_users", lambda: store)
    saved = {}
    monkeypatch.setattr(auth, "save_users", lambda u: saved.update(u))
    monkeypatch.setattr(auth, "is_admin", lambda u: u == "__admin__")
    # admin unchecks cardconv on a screen whose scope is only ["cardconv"]
    admin.handle("POST", "/admin/set_services",
                 {"username": ["someone@example.com"], "services": [],
                  "scope": ["cardconv"]}, {"user": "__admin__"})
    assert "timezones" in saved["someone@example.com"]["services"]
    assert "cardconv" not in saved["someone@example.com"]["services"]
