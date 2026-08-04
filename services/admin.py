from services import auth, email as email_svc

META = {
    "name": "Admin",
    "path": "/admin",
    "icon": "⚙️",
    "description": "Users and usage",
    "admin_only": True,
}

TABS = (("users", "👤 Users"), ("usage", "📊 Usage"))


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "")
    if not auth.is_admin(user):
        return ("html", _forbidden())

    if method == "GET" and path == "/admin/usage":
        # The Usage page became a tab; bookmarks and old links keep working.
        app = (body or {}).get("app", [""])[0]
        return ("redirect", "/admin?tab=usage" + (f"&app={app}" if app else ""))

    if method == "GET" and path == "/admin":
        tab = (body or {}).get("tab", ["users"])[0]
        return ("html", render_admin(user, tab=tab, query=body))

    if method == "POST" and path == "/admin/set_role":
        target = body.get("username", [""])[0].strip()
        role   = body.get("role", ["user"])[0]
        if target and target != user:
            auth.set_role(target, role)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/set_services":
        target = body.get("username", [""])[0].strip()
        services_raw = body.get("services", [])
        services_list = [s for s in services_raw if s in auth.CONTROLLED_SERVICES]
        # the form only manages the services in its scope — grants outside the
        # scope (hidden from the decluttered UI) are preserved untouched
        scope = [s for s in body.get("scope", [""])[0].split(",")
                 if s in auth.CONTROLLED_SERVICES]
        if target and target != user:
            users = auth.load_users()
            if target in users:
                cur = users[target].get("services", [])
                keep = [s for s in cur if s not in scope]
                users[target]["services"] = keep + [s for s in services_list if s in scope]
                auth.save_users(users)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/set_profile":
        target = body.get("username", [""])[0].strip()
        users = auth.load_users()
        if target in users:
            for k in ("company", "department", "drive_account"):
                users[target][k] = body.get(k, [""])[0].strip()
            if users[target]["company"] not in auth.OFFICES:
                users[target]["company"] = ""
            auth.save_users(users)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/reset_pw":
        # issue a one-time-shown temporary password (SMTP unset → admin relays
        # it to the user directly; user then changes it on the login page)
        import secrets as _secrets
        target = body.get("username", [""])[0].strip()
        users = auth.load_users()
        if target in users and target != user:
            alphabet = "abcdefghjkmnpqrstuvwxyz23456789"  # no 0/O/1/l/i
            temp = "".join(_secrets.choice(alphabet) for _ in range(10))
            users[target]["pw"] = auth.hash_pw(temp)
            auth.save_users(users)
            return ("html", render_admin(user, reset_result=(target, temp)))
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/block_user":
        target = body.get("username", [""])[0].strip()
        if target and target != user:
            auth.block_user(target)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/unblock_user":
        target = body.get("username", [""])[0].strip()
        if target and target != user:
            auth.unblock_user(target)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/delete_user":
        target = body.get("username", [""])[0].strip()
        if target and target != user:
            try:
                from services import cardconv as _cc
                _cc.purge_user_data(target)   # Drive token + cardconv data
            except Exception:
                pass
            auth.delete_user(target)          # login + data dir
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/toggle_service":
        svc = body.get("service", [""])[0].strip()
        if svc in auth.CONTROLLED_SERVICES:
            settings = auth.load_settings()
            avail = settings.get("available_services", [])
            if svc in avail:
                avail.remove(svc)
            else:
                avail.append(svc)
            settings["available_services"] = avail
            auth.save_settings(settings)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/tester/done":
        email = body.get("email", [""])[0].strip()
        if email:
            auth.remove_tester_request(email)
        return ("redirect", "/admin")

    if method == "POST" and path == "/admin/notify":
        subject = body.get("subject", [""])[0].strip()
        body_text = body.get("body", [""])[0].strip()
        if subject and body_text:
            users = auth.load_users()
            body_html = body_text.replace("\n", "<br>")
            sent, failed = 0, 0
            for uname, info in users.items():
                email_addr = info.get("email", "").strip()
                if not email_addr:
                    continue
                try:
                    email_svc.send(email_addr, subject, f"<p>{body_html}</p>")
                    sent += 1
                except Exception:
                    failed += 1
            return ("html", render_admin(
                user,
                notify_result=f"✅ Sent to {sent}"
                              + (f", ❌ {failed} failed" if failed else "")))
        return ("redirect", "/admin")

    # /admin/view/{username}/todo|habit
    parts = path.rstrip("/").split("/")
    if len(parts) >= 5 and parts[2] == "view":
        return _render_view(parts[3], parts[4], user)

    return ("html", render_admin(user))


def _render_view(target_user, service_name, admin_user):
    from services import todo as tsvc, habits as hsvc

    banner = (
        f'<div style="position:sticky;top:0;background:var(--amber-500);'
        f'color:var(--bg-deep);padding:9px 20px;font-size:.82rem;font-weight:700;'
        f'z-index:9999;display:flex;align-items:center;'
        f'justify-content:space-between;gap:12px">'
        f'<span>👁️ Admin view: <strong>{target_user}</strong> (read-only)</span>'
        f'<a href="/admin" style="color:var(--bg-deep);text-decoration:none;'
        f'font-weight:800">← Admin</a>'
        f'</div>'
    )

    if service_name == "todo":
        html = tsvc.render(tsvc.load(target_user), tsvc.load_habits(target_user),
                           target_user, readonly=True)
    elif service_name == "habit":
        html = hsvc.render_list(hsvc.load(target_user), target_user, readonly=True)
    else:
        return ("html", "<h2>404</h2>")

    html = html.replace("<body>\n", f"<body>\n{banner}\n", 1)
    return ("html", html)


def _forbidden():
    """The 403 is a page too — it gets the same shell as every other one."""
    return (
        '<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>Admin · Wayfinder</title>'
        '<link rel="stylesheet" href="/static/style.css"></head><body>'
        '<nav><a href="/admin" class="nav-brand">⚙️ Admin</a>'
        '<span class="nav-user"><a class="nav-back" href="/">← Home</a></span></nav>'
        '<div class="container"><div class="wf-empty-card" '
        'style="padding:40px 24px;text-align:center">'
        '<div class="wf-empty-icon">🚫</div>'
        '<div class="wf-empty-title">Admins only</div>'
        '<p class="wf-empty-sub">This page is restricted to administrator accounts.</p>'
        '<div class="wf-empty-actions"><a class="btn btn-secondary" href="/">← Back to Wayfinder</a></div>'
        '</div></div></body></html>'
    )


# Services shown in the per-user permission UI. Anything a person can be given
# individually belongs here; grants outside this list survive untouched
# (see the scope field) so trimming it never revokes anything.
_VISIBLE_SERVICES = ["momentum", "cardconv", "sow", "aeo", "llm-check", "toast"]


def _drive_token_exists(username):
    import os
    from services._paths import DATA_ROOT
    return os.path.exists(os.path.join(DATA_ROOT, "cardconv", "tokens", f"{username}.json"))


def render_admin(current_user, notify_result="", reset_result=None,
                 tab="users", query=None):
    users = auth.load_users()
    settings = auth.load_settings()
    available_svcs = settings.get("available_services", [])
    total = len(users)
    admin_count = sum(1 for v in users.values() if v.get("role") == "admin")
    svc_labels = auth.APP_LABELS

    rows = ""
    for username in sorted(users):
        info     = users[username]
        role     = info.get("role", "user")
        email_raw = info.get("email", "")
        email    = email_raw or "—"
        blocked  = info.get("blocked", False)
        is_self  = username == current_user
        is_adm   = role == "admin"

        # Office · department · the Google account linked to Drive (2026-07-24).
        # The Drive token carries no email, so it is typed in — accounts that do
        # hold a token get their login email offered as a guess.
        drive = info.get("drive_account", "")
        drive_guess = ""
        if not drive and _drive_token_exists(username):
            drive_guess = email_raw if "@" in email_raw else (username if "@" in username else "")
        cur_office = info.get("company", "")
        office_opts = '<option value="">— Office —</option>' + "".join(
            f'<option value="{o}"{" selected" if o == cur_office else ""}>{o}</option>'
            for o in auth.OFFICES)
        profile_col = f'''<form method="POST" action="/admin/set_profile" class="prof-form">
          <input type="hidden" name="username" value="{username}">
          <select name="company">{office_opts}</select>
          <input name="department" value="{info.get("department", "")}" placeholder="Department">
          <input name="drive_account" value="{drive or drive_guess}" placeholder="Drive Google account"
            {'class="is-guess" title="Guess, not saved — press Save to confirm"' if (not drive and drive_guess) else 'title="The Google account linked to Google Drive"'}>
          <button type="submit" class="svc-save-btn">Save</button>
        </form>'''

        name_cls = " is-blocked" if blocked else ""
        blocked_tag = ' <span class="badge blk-badge">🚫 Blocked</span>' if blocked else ""
        badge = (
            '<span class="badge adm-badge">🔑 Admin</span>' if is_adm
            else '<span class="badge usr-badge">👥 User</span>'
        )

        if is_self:
            control   = '<span class="self-tag">You</span>'
            svc_col   = '<span class="svc-all-badge">Full access</span>'
            action_col = ""
        elif is_adm:
            adm_active  = "seg-active adm-active"
            confirm_adm = f"return confirm('Remove admin rights from {username}?')"
            control = f'''<div class="seg-wrap">
              <form method="POST" action="/admin/set_role" style="display:contents">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="role" value="admin">
                <button class="seg-btn {adm_active}" type="submit">Admin</button>
              </form>
              <form method="POST" action="/admin/set_role" style="display:contents">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="role" value="user">
                <button class="seg-btn" type="submit" onclick="{confirm_adm}">User</button>
              </form>
            </div>'''
            svc_col   = '<span class="svc-all-badge">Full access</span>'
            action_col = ""  # admin accounts get no Block/Delete
        else:
            usr_active  = "seg-active"
            confirm_usr = f"return confirm('Give {username} admin rights?')"
            control = f'''<div class="seg-wrap">
              <form method="POST" action="/admin/set_role" style="display:contents">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="role" value="admin">
                <button class="seg-btn" type="submit" onclick="{confirm_usr}">Admin</button>
              </form>
              <form method="POST" action="/admin/set_role" style="display:contents">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="role" value="user">
                <button class="seg-btn {usr_active}" type="submit">User</button>
              </form>
            </div>'''
            user_svcs = set(info.get("services", []))
            # decluttered to AMEX only (강프로 2026-07-24) — other grants are
            # preserved via the scope field, just not shown here
            checks = "".join(
                f'<label class="svc-check"><input type="checkbox" name="services" value="{s}"'
                f'{" checked" if s in user_svcs else ""}> {svc_labels.get(s, s)}</label>'
                for s in _VISIBLE_SERVICES
            )
            svc_col = f'''<form method="POST" action="/admin/set_services" class="svc-form">
              <input type="hidden" name="username" value="{username}">
              <input type="hidden" name="scope" value="{",".join(_VISIBLE_SERVICES)}">
              {checks}
              <button type="submit" class="svc-save-btn">Save</button>
            </form>'''
            # Block / Unblock / Delete
            if blocked:
                block_btn = f'''<form method="POST" action="/admin/unblock_user" style="display:inline">
                  <input type="hidden" name="username" value="{username}">
                  <button type="submit" class="action-btn unblock-btn">✅ Unblock</button>
                </form>'''
            else:
                block_btn = f'''<form method="POST" action="/admin/block_user" style="display:inline">
                  <input type="hidden" name="username" value="{username}">
                  <button type="submit" class="action-btn block-btn" onclick="return confirm('Block {username}?')">🚫 Block</button>
                </form>'''
            delete_btn = f'''<form method="POST" action="/admin/delete_user" style="display:inline">
              <input type="hidden" name="username" value="{username}">
              <button type="submit" class="action-btn delete-btn" onclick="return confirm('Delete {username} for good? This cannot be undone.')">🗑 Delete</button>
            </form>'''
            reset_btn = f'''<form method="POST" action="/admin/reset_pw" style="display:inline">
              <input type="hidden" name="username" value="{username}">
              <button type="submit" class="action-btn resetpw-btn" onclick="return confirm('Issue a temporary password for {username}? The current one stops working.')">🔑 Reset PW</button>
            </form>'''
            action_col = f'<div class="action-stack">{reset_btn}{block_btn}{delete_btn}</div>'

        rows += f'''
        <tr class="{"row-self" if is_self else "row-blocked" if blocked else ""}">
          <td class="col-name">
            <span class="u-icon">{"🔑" if is_adm else "🚫" if blocked else "👤"}</span>
            <span class="u-name{name_cls}">{username}</span>{blocked_tag}
          </td>
          <td>{badge}</td>
          <td class="col-email">{email}</td>
          <td class="col-profile">{profile_col}</td>
          <td class="col-svc">{svc_col}</td>
          <td>{control}</td>
          <td class="col-action">{action_col}</td>
        </tr>'''

    # Global service toggles
    global_toggles = ""
    for svc in sorted(auth.CONTROLLED_SERVICES):
        is_on = svc in available_svcs
        btn_cls = "gtoggle-on" if is_on else "gtoggle-off"
        btn_txt = f'{"✅" if is_on else "⬜"} {svc_labels.get(svc, svc)} ({"on" if is_on else "off"})'
        global_toggles += f'''
        <form method="POST" action="/admin/toggle_service" style="display:inline">
          <input type="hidden" name="service" value="{svc}">
          <button type="submit" class="gtoggle-btn {btn_cls}">{btn_txt}</button>
        </form>'''

    # Google OAuth test-user queue
    tester_reqs = auth.load_tester_requests()
    if tester_reqs:
        tester_rows = ""
        for r in tester_reqs:
            email = r.get("email", "")
            by    = r.get("requested_by", "") or "—"
            when  = (r.get("requested_at", "") or "")[:10]
            tester_rows += f'''
            <tr>
              <td class="tq-email">{email}</td>
              <td class="tq-meta">{by}</td>
              <td class="tq-meta">{when}</td>
              <td>
                <form method="POST" action="/admin/tester/done" style="display:inline">
                  <input type="hidden" name="email" value="{email}">
                  <button type="submit" class="action-btn unblock-btn">✅ Done</button>
                </form>
              </td>
            </tr>'''
        all_emails = ", ".join(r.get("email", "") for r in tester_reqs)
        tester_section = f'''
  <div class="section-card">
    <h2>🧪 Tester queue <span class="sec-count">({len(tester_reqs)})</span></h2>
    <p class="sec-desc">Google has no API for adding test users. Paste these emails into
      <a href="https://console.cloud.google.com/auth/audience" target="_blank" class="sec-link">OAuth consent screen → Test users</a>,
      register them, then press Done.</p>
    <button type="button" class="notify-send-btn spaced"
      onclick="navigator.clipboard.writeText('{all_emails}').then(()=>{{this.textContent='✅ Copied';setTimeout(()=>this.textContent='📋 Copy all emails',1500)}})">📋 Copy all emails</button>
    <div class="tbl-wrap flush">
      <table>
        <thead><tr><th>Google email</th><th>Requested by</th><th>Requested</th><th>Action</th></tr></thead>
        <tbody>{tester_rows}</tbody>
      </table>
    </div>
  </div>'''
    else:
        tester_section = ""

    notify_msg = f'<div class="notify-result">{notify_result}</div>' if notify_result else ""
    reset_banner = ""
    if reset_result:
        r_user, r_temp = reset_result
        reset_banner = f'''<div class="reset-banner">🔑 Temporary password for <b>{r_user}</b>:
      <code id="tempPw">{r_temp}</code>
      <button type="button" class="notify-send-btn btn-tiny"
        onclick="navigator.clipboard.writeText('{r_temp}').then(()=>{{this.textContent='✅ Copied'}})">📋 Copy</button>
      <div class="reset-note">Leave this page and it is gone. Hand it over, and have them
        set a new one via "Change password" on the login page.</div>
    </div>'''

    from services import _usage
    tab = tab if tab in dict(TABS) else "users"
    tabs_html = "".join(
        f'<a class="adm-tab{" active" if key == tab else ""}" href="/admin?tab={key}"'
        f'{" aria-current=\'true\'" if key == tab else ""}>{lab}</a>'
        for key, lab in TABS)

    users_body = f'''
  <div class="summary">
    <div class="sum-card"><span class="sum-val">{total}</span><span class="sum-lbl">Total users</span></div>
    <div class="sum-card"><span class="sum-val accent">{admin_count}</span><span class="sum-lbl">Admin</span></div>
    <div class="sum-card"><span class="sum-val muted">{total - admin_count}</span><span class="sum-lbl">User</span></div>
  </div>

  {reset_banner}
  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th>User</th>
          <th>Role</th>
          <th>Email</th>
          <th class="col-profile">Office · Department · Drive</th>
          <th class="col-svc">Service access</th>
          <th>Role change</th>
          <th>Manage</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <div class="section-card">
    <h2>🌐 Global service control</h2>
    <p class="sec-desc">Which services a new account can pick on the signup form.</p>
    {global_toggles}
  </div>
{tester_section}
  <div class="section-card">
    <h2>📢 Broadcast</h2>
    <p class="sec-desc">Goes to every user who has an email on file.</p>
    {notify_msg}
    <form method="POST" action="/admin/notify" class="notify-form">
      <input name="subject" placeholder="Subject" required>
      <textarea name="body" placeholder="Message (line breaks kept)"></textarea>
      <button type="submit" class="notify-send-btn">📨 Send</button>
    </form>
  </div>'''

    body = users_body if tab == "users" else _usage.render_body(current_user, query)

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>⚙️ Admin · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.container{{max-width:1500px}}
h1{{margin:0;padding-top:32px}}
h2{{font-size:1rem;font-weight:800;color:var(--text);margin:0 0 14px}}
.adm-head{{display:flex;justify-content:space-between;align-items:flex-end;gap:16px;flex-wrap:wrap}}
.adm-tabs{{display:inline-flex;gap:4px;background:var(--surface-2);border-radius:var(--radius-full);
  padding:4px;margin:18px 0 22px}}
.adm-tab{{padding:9px 20px;border-radius:var(--radius-full);font-size:.88rem;font-weight:700;
  color:var(--text-muted);text-decoration:none;white-space:nowrap;min-height:44px;
  display:inline-flex;align-items:center}}
.adm-tab.active{{background:var(--accent);color:var(--bg-deep)}}
.summary{{display:flex;gap:12px;margin-bottom:22px;flex-wrap:wrap}}
.sum-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);
  padding:14px 22px;display:flex;flex-direction:column;gap:4px}}
.sum-val{{font-size:1.5rem;font-weight:800;color:var(--text)}}
.sum-val.accent{{color:var(--accent)}}
.sum-val.muted{{color:var(--text-muted)}}
.sum-lbl{{font-size:.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em}}
.tbl-wrap{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);
  overflow:auto;margin-bottom:24px}}
.tbl-wrap.flush{{margin-bottom:0}}
table{{width:100%;border-collapse:collapse;min-width:900px}}
thead tr{{background:var(--surface-2)}}
th{{text-align:left;padding:12px 16px;font-size:.72rem;color:var(--text-muted);text-transform:uppercase;
  letter-spacing:.05em;font-weight:700;border-bottom:1px solid var(--border);white-space:nowrap}}
td{{padding:12px 16px;border-bottom:1px solid var(--border);vertical-align:middle;color:var(--text)}}
tr:last-child td{{border-bottom:none}}
tr.row-self{{background:var(--surface-2)}}
tr.row-blocked td{{opacity:.65}}
.prof-form{{display:flex;flex-direction:column;gap:4px;min-width:170px}}
.prof-form input,.prof-form select{{padding:6px 8px;border:1px solid var(--border-bright);
  border-radius:var(--radius-sm);font-size:.78rem;outline:none;background:var(--surface-2);color:var(--text)}}
.prof-form input:focus,.prof-form select:focus{{border-color:var(--accent)}}
.prof-form .is-guess{{color:var(--text-muted)}}
.prof-form .svc-save-btn{{align-self:flex-start}}
.col-name{{white-space:nowrap}}
.col-name .u-icon{{margin-right:8px}}
.u-icon{{font-size:1.1rem}}
.u-name{{font-size:.88rem;font-weight:700;color:var(--text)}}
.u-name.is-blocked{{color:var(--red-500);text-decoration:line-through}}
.col-email{{font-size:.82rem;color:var(--text-muted);max-width:180px;overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}}
.badge{{font-size:.72rem;font-weight:700;padding:4px 10px;border-radius:var(--radius-full);white-space:nowrap}}
.adm-badge{{background:var(--accent-glow);color:var(--accent)}}
.usr-badge{{background:var(--surface-2);color:var(--text-muted)}}
.blk-badge{{background:var(--surface-2);color:var(--red-500)}}
.svc-all-badge{{font-size:.72rem;color:var(--green-500);background:var(--surface-2);
  border:1px solid var(--border-bright);padding:4px 10px;border-radius:var(--radius-full);white-space:nowrap}}
.svc-form{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.svc-check{{display:flex;align-items:center;gap:4px;font-size:.78rem;color:var(--text-muted);
  cursor:pointer;white-space:nowrap;min-height:32px}}
.svc-save-btn{{padding:6px 12px;background:var(--accent);color:var(--bg-deep);border:none;
  border-radius:var(--radius-sm);font-size:.78rem;font-weight:700;cursor:pointer;white-space:nowrap}}
.seg-wrap{{display:inline-flex;background:var(--surface-2);border-radius:var(--radius-md);padding:2px}}
.seg-btn{{padding:7px 14px;border:none;background:transparent;color:var(--text-muted);font-size:.78rem;
  font-weight:700;cursor:pointer;border-radius:var(--radius-sm);white-space:nowrap}}
.seg-btn.seg-active{{background:var(--surface);color:var(--text)}}
.seg-btn.adm-active{{background:var(--accent);color:var(--bg-deep)}}
.self-tag{{font-size:.78rem;color:var(--text-muted);padding:6px 12px;background:var(--surface-2);
  border-radius:var(--radius-sm);border:1px solid var(--border)}}
.section-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:22px;margin-bottom:22px}}
.sec-desc{{font-size:.82rem;color:var(--text-muted);margin-bottom:16px}}
.sec-count{{font-size:.8rem;color:var(--text-muted);font-weight:600}}
.sec-link{{color:var(--accent)}}
.gtoggle-btn{{padding:10px 18px;border:1px solid var(--border-bright);border-radius:var(--radius-md);
  font-size:.82rem;font-weight:700;cursor:pointer;margin:0 8px 8px 0;min-height:44px}}
.gtoggle-on{{background:var(--accent-glow);color:var(--accent);border-color:var(--accent)}}
.gtoggle-off{{background:var(--surface-2);color:var(--text-muted)}}
.notify-form{{display:flex;flex-direction:column;gap:12px}}
.notify-form input,.notify-form textarea{{width:100%;padding:12px 14px;border:1px solid var(--border-bright);
  border-radius:var(--radius-md);font-size:.92rem;outline:none;font-family:inherit;
  background:var(--surface-2);color:var(--text);min-height:44px}}
.notify-form input:focus,.notify-form textarea:focus{{border-color:var(--accent)}}
.notify-form textarea{{min-height:100px;resize:vertical}}
.notify-send-btn{{align-self:flex-start;padding:11px 22px;background:var(--accent);color:var(--bg-deep);
  border:none;border-radius:var(--radius-md);font-size:.88rem;font-weight:700;cursor:pointer;min-height:44px}}
.notify-send-btn.spaced{{margin-bottom:14px}}
.notify-send-btn.btn-tiny{{padding:4px 12px;font-size:.75rem;min-height:32px}}
.notify-result{{padding:10px 16px;background:var(--surface-2);border:1px solid var(--border-bright);
  border-radius:var(--radius-md);color:var(--green-500);font-size:.82rem;margin-bottom:16px}}
.action-btn{{padding:6px 10px;border:1px solid var(--border-bright);border-radius:var(--radius-sm);
  font-size:.75rem;font-weight:700;cursor:pointer;white-space:nowrap;background:var(--surface-2);color:var(--text)}}
.block-btn{{color:var(--amber-500)}}
.unblock-btn{{color:var(--green-500)}}
.delete-btn{{color:var(--red-500)}}
.resetpw-btn{{color:var(--accent)}}
.reset-banner{{background:var(--surface);border:1px solid var(--amber-500);border-radius:var(--radius-md);
  padding:14px 18px;margin-bottom:16px;font-size:.9rem;color:var(--text)}}
.reset-banner code{{background:var(--surface-2);color:var(--amber-500);padding:3px 10px;
  border-radius:var(--radius-sm);font-size:.95rem;letter-spacing:.06em;margin:0 6px}}
.reset-note{{font-size:.75rem;color:var(--text-muted);margin-top:6px}}
.action-stack{{display:flex;flex-direction:column;gap:6px;width:104px}}
.action-stack form{{display:block!important}}
.action-stack .action-btn{{width:100%;text-align:center}}
.tq-email{{font-size:.82rem;font-weight:700;color:var(--text)}}
.tq-meta{{font-size:.78rem;color:var(--text-muted);white-space:nowrap}}
{_usage.USAGE_CSS}
@media(max-width:768px){{
  h1{{padding-top:22px;font-size:1.4rem}}
  .adm-tabs{{display:flex;width:100%}}
  .adm-tab{{flex:1;justify-content:center;padding:9px 8px}}
  .section-card{{padding:16px}}
  .sum-card{{padding:12px 16px;flex:1;min-width:96px}}
  td,th{{padding:10px 12px;vertical-align:top}}
  /* Editing a stacked profile form or a checkbox grid on a phone is not the
     job — scanning who exists is. Those columns drag every row to ~250px tall
     while sitting off-screen, so they stand down until there is width. */
  .col-profile,.col-svc{{display:none}}
  table{{min-width:0}}
}}
</style>
</head><body>
<nav>
  <a href="/admin" class="nav-brand">⚙️ Admin</a>
  <span class="nav-user">🔑 {current_user} &nbsp;·&nbsp; <a href="/">← Wayfinder</a>
    &nbsp;·&nbsp; <a href="/logout">Log out</a></span>
</nav>
<div class="container">
  <h1>⚙️ Admin</h1>
  <div class="adm-tabs" role="group" aria-label="Admin sections">{tabs_html}</div>
  {body}
</div>
</body></html>'''
