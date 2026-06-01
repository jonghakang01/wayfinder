from services import auth, email as email_svc

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

    if method == "POST" and path == "/admin/set_services":
        target = body.get("username", [""])[0].strip()
        services_raw = body.get("services", [])
        services_list = [s for s in services_raw if s in auth.CONTROLLED_SERVICES]
        if target and target != user:
            users = auth.load_users()
            if target in users:
                users[target]["services"] = services_list
                auth.save_users(users)
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
            auth.delete_user(target)
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
            return ("html", render_admin(user, notify_result=f"✅ {sent}명 발송 완료" + (f", ❌ {failed}명 실패" if failed else "")))
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


def render_admin(current_user, notify_result=""):
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
        email    = info.get("email", "") or "—"
        blocked  = info.get("blocked", False)
        is_self  = username == current_user
        is_adm   = role == "admin"

        name_style = "color:#ef4444;text-decoration:line-through" if blocked else ""
        blocked_tag = ' <span class="badge" style="background:#fee2e2;color:#b91c1c;font-size:11px">🚫 Blocked</span>' if blocked else ""
        badge = (
            '<span class="badge adm-badge">🔑 Admin</span>' if is_adm
            else '<span class="badge usr-badge">👥 User</span>'
        )

        if is_self:
            control   = '<span class="self-tag">본인</span>'
            svc_col   = '<span class="svc-all-badge">전체 접근</span>'
            action_col = ""
        elif is_adm:
            adm_active  = "seg-active adm-active"
            confirm_adm = f"return confirm('{username}님의 Admin 권한을 제거할까요?')"
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
            svc_col   = '<span class="svc-all-badge">전체 접근</span>'
            action_col = ""  # Admin 계정은 Block/Delete 없음
        else:
            usr_active  = "seg-active"
            confirm_usr = f"return confirm('{username}님에게 Admin 권한을 부여할까요?')"
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
            checks = "".join(
                f'<label class="svc-check"><input type="checkbox" name="services" value="{s}"'
                f'{" checked" if s in user_svcs else ""}> {svc_labels.get(s, s)}</label>'
                for s in sorted(auth.CONTROLLED_SERVICES)
            )
            svc_col = f'''<form method="POST" action="/admin/set_services" class="svc-form">
              <input type="hidden" name="username" value="{username}">
              {checks}
              <button type="submit" class="svc-save-btn">저장</button>
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
                  <button type="submit" class="action-btn block-btn" onclick="return confirm('{username}님을 차단할까요?')">🚫 Block</button>
                </form>'''
            delete_btn = f'''<form method="POST" action="/admin/delete_user" style="display:inline">
              <input type="hidden" name="username" value="{username}">
              <button type="submit" class="action-btn delete-btn" onclick="return confirm('{username}님을 완전히 삭제할까요? 되돌릴 수 없습니다.')">🗑 Delete</button>
            </form>'''
            action_col = block_btn + " " + delete_btn

        rows += f'''
        <tr class="{"row-self" if is_self else "row-blocked" if blocked else ""}">
          <td class="col-name">
            <span class="u-icon">{"🔑" if is_adm else "🚫" if blocked else "👤"}</span>
            <span class="u-name" style="{name_style}">{username}</span>{blocked_tag}
          </td>
          <td>{badge}</td>
          <td class="col-email">{email}</td>
          <td>{svc_col}</td>
          <td>{control}</td>
          <td class="col-action">{action_col}</td>
        </tr>'''

    # 전역 서비스 토글
    global_toggles = ""
    for svc in sorted(auth.CONTROLLED_SERVICES):
        is_on = svc in available_svcs
        btn_cls = "gtoggle-on" if is_on else "gtoggle-off"
        btn_txt = f'{"✅" if is_on else "⬜"} {svc_labels.get(svc, svc)} ({"활성" if is_on else "비활성"})'
        global_toggles += f'''
        <form method="POST" action="/admin/toggle_service" style="display:inline">
          <input type="hidden" name="service" value="{svc}">
          <button type="submit" class="gtoggle-btn {btn_cls}">{btn_txt}</button>
        </form>'''

    notify_msg = f'<div class="notify-result">{notify_result}</div>' if notify_result else ""

    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⚙️ 관리자 페이지</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.container{{ max-width: 980px; }}
h1{{ margin-top: 0; padding-top: 40px; }}
h2{{ font-size:16px;font-weight:700;color:#1e293b;margin-bottom:14px }}
.summary{{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}}
.sum-card{{background:white;border:1px solid #e2e8f0;border-radius:10px;padding:14px 22px;display:flex;flex-direction:column;gap:4px}}
.sum-val{{font-size:24px;font-weight:700;color:#1a1a1a}}
.sum-lbl{{font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.4px}}
.tbl-wrap{{background:white;border:1px solid #e2e8f0;border-radius:12px;overflow:auto;margin-bottom:32px}}
table{{width:100%;border-collapse:collapse;min-width:700px}}
thead tr{{background:#f8fafc}}
th{{text-align:left;padding:12px 16px;font-size:12px;color:#64748b;text-transform:uppercase;letter-spacing:.5px;font-weight:600;border-bottom:1px solid #e2e8f0;white-space:nowrap}}
td{{padding:12px 16px;border-bottom:1px solid #f1f5f9;vertical-align:middle}}
tr:last-child td{{border-bottom:none}}
tr.row-self{{background:#f0f9ff}}
.col-name{{display:flex;align-items:center;gap:10px}}
.u-icon{{font-size:18px}}
.u-name{{font-size:14px;font-weight:600;color:#1e293b}}
.col-email{{font-size:13px;color:#64748b;max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.badge{{font-size:12px;font-weight:600;padding:4px 10px;border-radius:20px;white-space:nowrap}}
.adm-badge{{background:#dbeafe;color:#1d4ed8}}
.usr-badge{{background:#f1f5f9;color:#475569}}
.svc-all-badge{{font-size:12px;color:#166534;background:#f0fdf4;border:1px solid #bbf7d0;padding:4px 10px;border-radius:20px;white-space:nowrap}}
.svc-form{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.svc-check{{display:flex;align-items:center;gap:4px;font-size:12px;color:#475569;cursor:pointer;white-space:nowrap}}
.svc-save-btn{{padding:4px 10px;background:#3b82f6;color:white;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap}}
.svc-save-btn:hover{{background:#2563eb}}
.seg-wrap{{display:inline-flex;background:#f1f5f9;border-radius:8px;padding:2px;gap:0}}
.seg-btn{{padding:5px 13px;border:none;background:transparent;color:#64748b;font-size:12px;font-weight:600;cursor:pointer;border-radius:6px;transition:all .15s;white-space:nowrap}}
.seg-btn.seg-active{{background:white;color:#1e293b;box-shadow:0 1px 3px rgba(0,0,0,.12)}}
.seg-btn.adm-active{{background:#3b82f6;color:white;box-shadow:0 1px 3px rgba(59,130,246,.4)}}
.self-tag{{font-size:12px;color:#94a3b8;padding:5px 12px;background:#f8fafc;border-radius:6px;border:1px solid #e2e8f0}}
.col-view{{display:flex;gap:8px;align-items:center;flex-wrap:wrap}}
.view-btn{{font-size:12px;font-weight:600;padding:6px 12px;border-radius:6px;text-decoration:none;background:#f0fdf4;color:#166534;border:1px solid #bbf7d0;white-space:nowrap;transition:background .15s}}
.view-btn:hover{{background:#dcfce7}}
.section-card{{background:white;border:1px solid #e2e8f0;border-radius:12px;padding:24px;margin-bottom:24px}}
.gtoggle-btn{{padding:8px 18px;border:none;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;margin-right:8px;margin-bottom:8px}}
.gtoggle-on{{background:#dcfce7;color:#166534;border:1px solid #bbf7d0}}
.gtoggle-off{{background:#f1f5f9;color:#64748b;border:1px solid #e2e8f0}}
.notify-form{{display:flex;flex-direction:column;gap:12px}}
.notify-form input,.notify-form textarea{{width:100%;padding:10px 14px;border:1px solid #e2e8f0;border-radius:8px;font-size:14px;outline:none;font-family:inherit}}
.notify-form input:focus,.notify-form textarea:focus{{border-color:#3b82f6}}
.notify-form textarea{{min-height:100px;resize:vertical}}
.notify-send-btn{{align-self:flex-start;padding:9px 22px;background:#3b82f6;color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer}}
.notify-send-btn:hover{{background:#2563eb}}
.notify-result{{padding:10px 16px;background:#f0fdf4;border:1px solid #bbf7d0;border-radius:8px;color:#166534;font-size:13px;margin-bottom:16px}}
.sec-desc{{font-size:13px;color:#64748b;margin-bottom:16px}}
.action-btn{{padding:4px 10px;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;white-space:nowrap}}
.block-btn{{background:#fef3c7;color:#92400e;border:1px solid #fde68a}}
.block-btn:hover{{background:#fde68a}}
.unblock-btn{{background:#d1fae5;color:#065f46;border:1px solid #6ee7b7}}
.unblock-btn:hover{{background:#a7f3d0}}
.delete-btn{{background:#fee2e2;color:#991b1b;border:1px solid #fca5a5}}
.delete-btn:hover{{background:#fca5a5}}
.col-action{{display:flex;gap:6px;align-items:center;flex-wrap:wrap}}
tr.row-blocked td{{opacity:.65;background:#fff5f5}}
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
          <th>역할</th>
          <th>이메일</th>
          <th>서비스 권한</th>
          <th>권한 변경</th>
          <th>관리</th>
        </tr>
      </thead>
      <tbody>{rows}</tbody>
    </table>
  </div>

  <div class="section-card">
    <h2>🌐 전역 서비스 제어</h2>
    <p class="sec-desc">신규 가입 폼에서 선택 가능한 서비스를 제어합니다.</p>
    {global_toggles}
  </div>

  <div class="section-card">
    <h2>📢 전체 공지 발송</h2>
    <p class="sec-desc">이메일이 등록된 모든 사용자에게 발송됩니다.</p>
    {notify_msg}
    <form method="POST" action="/admin/notify" class="notify-form">
      <input name="subject" placeholder="제목" required>
      <textarea name="body" placeholder="내용 (줄바꿈 지원)"></textarea>
      <button type="submit" class="notify-send-btn">📨 발송</button>
    </form>
  </div>
</div>
</body></html>'''
