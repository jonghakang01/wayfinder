from services import auth

META = {
    "name": "관리자",
    "path": "/admin",
    "icon": "⚙️",
    "description": "사용자 권한 관리",
    "admin_only": True,
}


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "")
    if not auth.is_admin(user):
        return ("html", _forbidden())

    if method == "POST" and path == "/admin/set_role":
        target = body.get("username", [""])[0].strip()
        role   = body.get("role", ["user"])[0]
        if target and target != user:
            auth.set_role(target, role)
        return ("redirect", "/admin")

    # /admin/view/{username}/todo|habit
    parts = path.rstrip("/").split("/")
    if len(parts) >= 5 and parts[2] == "view":
        return _render_view(parts[3], parts[4], user)

    return ("html", render_admin(user))


def _render_view(target_user, service_name, admin_user):
    from services import todo as tsvc, habits as hsvc

    banner = (
        f'<div style="position:sticky;top:0;background:#f59e0b;color:#1c1917;'
        f'padding:9px 20px;font-size:13px;font-weight:600;z-index:9999;'
        f'display:flex;align-items:center;justify-content:space-between;'
        f'border-bottom:2px solid #d97706">'
        f'<span>👁️ 관리자 열람: <strong>{target_user}</strong>님의 데이터 (읽기 전용)</span>'
        f'<a href="/admin" style="color:#1c1917;text-decoration:none;font-weight:700">← 관리자 페이지</a>'
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
    return (
        '<!DOCTYPE html><html><body style="text-align:center;padding:80px;font-family:sans-serif">'
        '<h2>🚫 권한 없음</h2><p>관리자만 접근할 수 있습니다.</p>'
        '<a href="/">← 홈으로</a></body></html>'
    )


def render_admin(current_user):
    users = auth.load_users()
    total = len(users)
    admin_count = sum(1 for v in users.values() if v.get("role") == "admin")

    rows = ""
    for username in sorted(users):
        info = users[username]
        role     = info.get("role", "user")
        is_self  = username == current_user
        is_adm   = role == "admin"

        badge = (
            '<span class="badge adm-badge">🔑 Admin</span>' if is_adm
            else '<span class="badge usr-badge">👥 User</span>'
        )

        if is_self:
            control  = '<span class="self-tag">본인</span>'
            view_col = ""
        else:
            adm_active = "seg-active adm-active" if is_adm  else ""
            usr_active = "seg-active"             if not is_adm else ""
            confirm_adm = "" if not is_adm else f'onclick="return confirm(\'{username}님의 Admin 권한을 제거할까요?\')"'
            confirm_usr = "" if is_adm else f'onclick="return confirm(\'{username}님에게 Admin 권한을 부여할까요?\')"'
            control = f'''
            <div class="seg-wrap">
              <form method="POST" action="/admin/set_role" style="display:contents">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="role" value="admin">
                <button class="seg-btn {adm_active}" type="submit" {confirm_usr}>Admin</button>
              </form>
              <form method="POST" action="/admin/set_role" style="display:contents">
                <input type="hidden" name="username" value="{username}">
                <input type="hidden" name="role" value="user">
                <button class="seg-btn {usr_active}" type="submit" {confirm_adm}>User</button>
              </form>
            </div>'''
            view_col = f'''
            <a href="/admin/view/{username}/todo"  class="view-btn">📋 Todo</a>
            <a href="/admin/view/{username}/habit" class="view-btn">🏃 습관</a>'''

        rows += f'''
        <tr class="{"row-self" if is_self else ""}">
          <td class="col-name">
            <span class="u-icon">{"🔑" if is_adm else "👤"}</span>
            <span class="u-name">{username}</span>
          </td>
          <td>{badge}</td>
          <td>{control}</td>
          <td class="col-view">{view_col}</td>
        </tr>'''

    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚙️ 관리자 페이지</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.container{{ max-width: 760px; }}
h1{{ margin-top: 0; padding-top: 40px; }}
.summary{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
.sum-card{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px 22px;display:flex;flex-direction:column;gap:4px}}
.sum-val{{font-size:24px;font-weight:700;color:#1a1a1a}}
.sum-lbl{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.4px}}
.tbl-wrap{{background:white;border:1px solid #e2e8f0;border-radius:12px;overflow:hidden}}
table{{width:100%;border-collapse:collapse}}
thead tr{{background:#f8fafc}}
th{{text-align:left;padding:12px 16px;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600;border-bottom:1px solid #e2e8f0}}
td{{padding:14px 16px;border-bottom:1px solid #f1f5f9;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}
tr.row-self{{background:#f0f9ff}}
.col-name{{display:flex;align-items:center;gap:10px}}
.u-icon{{font-size:18px}}
.u-name{{font-size:14px;font-weight:600;color:#1e293b}}
.badge{{font-size:12px;font-weight:600;padding:4px 10px;border-radius:20px;white-space:nowrap}}
.adm-badge{{background:#dbeafe;color:#1d4ed8}}
.usr-badge{{background:#f1f5f9;color:#475569}}
.seg-wrap{{display:inline-flex;background:#f1f5f9;border-radius:8px;padding:2px;gap:0}}
.seg-btn{{padding:5px 13px;border:none;background:transparent;color:#64748b;font-size:12px;font-weight:600;cursor:pointer;border-radius:6px;transition:all .15s;white-space:nowrap}}
.seg-btn.seg-active{{background:white;color:#1e293b;box-shadow:0 1px 3px rgba(0,0,0,.12)}}
.seg-btn.adm-active{{background:#3b82f6;color:white;box-shadow:0 1px 3px rgba(59,130,246,.4)}}
.self-tag{{font-size:12px;color:#94a3b8;padding:5px 12px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0}}
.col-view{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.view-btn{{font-size:12px;font-weight:600;padding:6px 12px;border-radius:6px;text-decoration:none;background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;white-space:nowrap;transition:background .15s}}
.view-btn:hover{{background:#dcfce7}}
</style>
</head><body>
<nav>
  <a href="/">← Wayfinder</a>
  <span class="nav-user">🔑 {current_user} &nbsp;·&nbsp; <a href="/logout">로그아웃</a></span>
</nav>
<div class="container">
  <h1>⚙️ 관리자 페이지</h1>

  <div class="summary">
    <div class="sum-card"><span class="sum-val">{total}</span><span class="sum-lbl">전체 사용자</span></div>
    <div class="sum-card"><span class="sum-val" style="color:#1d4ed8">{admin_count}</span><span class="sum-lbl">Admin</span></div>
    <div class="sum-card"><span class="sum-val" style="color:#475569">{total - admin_count}</span><span class="sum-lbl">User</span></div>
  </div>

  <div class="tbl-wrap">
    <table>
      <thead>
        <tr>
          <th>사용자</th>
          <th>권한</th>
          <th>권한 변경</th>
          <th>데이터 열람</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>
</div>
</body></html>'''
