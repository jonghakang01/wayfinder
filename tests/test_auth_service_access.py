"""A grant must open every route it absorbed.

Tasks, Habits and Today were folded into Momentum, but their POST routes kept
their own paths. The access check read the alias map one way only, so an
account granted 'momentum' could open the Tasks page and then be thrown to the
home page the moment it added a task — every non-admin user, every add.
"""
import services.auth as auth


def _granted(monkeypatch, services):
    monkeypatch.setattr(auth, "load_users",
                        lambda: {"someone@example.com": {"services": services}})
    monkeypatch.setattr(auth, "is_admin", lambda u: False)
    return "someone@example.com"


def test_momentum_grant_opens_absorbed_routes(monkeypatch):
    user = _granted(monkeypatch, ["momentum"])
    for path in ("/momentum", "/todo", "/habit", "/dashboard"):
        assert auth.has_service_access(user, path), path


def test_legacy_todo_grant_still_opens_momentum(monkeypatch):
    """Accounts predating the merge hold 'todo' and must not lose the app."""
    user = _granted(monkeypatch, ["todo"])
    assert auth.has_service_access(user, "/momentum")
    assert auth.has_service_access(user, "/todo")


def test_grant_does_not_leak_to_other_services(monkeypatch):
    user = _granted(monkeypatch, ["momentum"])
    assert not auth.has_service_access(user, "/cardconv")
    assert not auth.has_service_access(user, "/sow")


def test_blocked_user_reaches_nothing(monkeypatch):
    monkeypatch.setattr(auth, "load_users",
                        lambda: {"x@example.com": {"services": ["momentum"],
                                                   "blocked": True}})
    monkeypatch.setattr(auth, "is_admin", lambda u: False)
    assert not auth.has_service_access("x@example.com", "/todo")
