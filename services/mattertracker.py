"""Matter Tracker — launcher card for the local matter-tracker app.

The tracker itself runs ONLY on Jongha's machine (localhost:8765): it reads the
local Outlook mailbox and its data never leaves the PC. Wayfinder just gives it
a home-screen card; the route redirects to the local server, which works from
both the local and prod home pages because the browser sits on the same PC.
"""

META = {
    "name": "Matter Tracker",
    "path": "/matters",
    "icon": "🗂",
    "description": "Outlook 사안 추적 — 공 소재·브릿지 관계도 (로컬 전용)",
    "admin_only": True,
}


def handle(method, path, body, ctx=None):
    return ("redirect", "http://localhost:8765")
