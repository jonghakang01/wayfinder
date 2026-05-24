import os, re, subprocess, json
from datetime import datetime
from pathlib import Path

META = {
    "name": "워크스페이스",
    "path": "/workspace",
    "icon": "🖥️",
    "description": "터미널 + 파일 업로드",
}

UPLOAD_DIR = os.path.expanduser("~/uploads")
PROJECTS_DIR = Path.home() / "projects"
TTYD_PORT = 7681
TTYD_BIN = os.path.expanduser("~/bin/ttyd")
DASHBOARD_URL = "http://localhost:8765"


def list_projects():
    projects = []
    if not PROJECTS_DIR.exists():
        return projects
    for p in sorted(PROJECTS_DIR.iterdir()):
        if not p.is_dir() or p.name.startswith('.'):
            continue
        meta_file = p / "meta.json"
        meta = {}
        if meta_file.exists():
            try:
                meta = json.loads(meta_file.read_text())
            except Exception:
                pass
        files = sorted(
            [f.name for f in p.iterdir() if not f.name.startswith('.') and f.is_file()],
        )
        projects.append({
            "id": p.name,
            "name": meta.get("name", p.name),
            "color": meta.get("color", "#6366f1"),
            "status": meta.get("status", "active"),
            "files": files,
        })
    return projects


def _ensure_ttyd():
    result = subprocess.run(["pgrep", "-f", f"ttyd.*{TTYD_PORT}"], capture_output=True)
    if result.returncode != 0:
        subprocess.Popen(
            [TTYD_BIN, "-p", str(TTYD_PORT), "--writable", "bash", "-c",
             "tmux attach-session -t 'team:쭌' 2>/dev/null || bash"],
            stdout=open("/tmp/ttyd_7681.log", "w"),
            stderr=subprocess.STDOUT,
        )


def _ensure_upload_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def list_files():
    _ensure_upload_dir()
    files = []
    for f in sorted(os.listdir(UPLOAD_DIR), reverse=True):
        path = os.path.join(UPLOAD_DIR, f)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            size_str = f"{size // 1024}KB" if size >= 1024 else f"{size}B"
            files.append({"name": f, "size": size_str, "mtime": mtime.strftime("%m/%d %H:%M")})
    return files


def _get(body, key):
    v = body.get(key, "")
    return v[0] if isinstance(v, list) else (v or "")


def handle(method, path, body, ctx):
    _ensure_ttyd()
    _ensure_upload_dir()

    if method == "GET" and path == "/workspace":
        return ("html", render_workspace())

    if method == "POST" and path == "/workspace/upload":
        raw = body.get("__raw__")
        if raw:
            return handle_upload(raw)
        return ("json", {"error": "업로드 데이터 없음"})

    if method == "POST" and path == "/workspace/delete":
        fname = _get(body, "filename")
        if fname and ".." not in fname:
            fpath = os.path.join(UPLOAD_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
        return ("redirect", "/workspace")

    return ("html", "<h2>404</h2>", 404)


def handle_upload(handler):
    content_type = handler.headers.get("Content-Type", "")
    length = int(handler.headers.get("Content-Length", 0))
    if "multipart/form-data" not in content_type:
        return ("json", {"error": "multipart 형식 필요"})
    try:
        m = re.search(r'boundary=([^\s;]+)', content_type)
        if not m:
            return ("json", {"error": "boundary 없음"})
        boundary = ("--" + m.group(1)).encode()
        data = handler.rfile.read(length)
        saved = []
        for part in data.split(boundary):
            if b'filename="' not in part:
                continue
            fname_m = re.search(rb'filename="([^"]+)"', part)
            if not fname_m:
                continue
            safe_name = os.path.basename(fname_m.group(1).decode())
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            dest = os.path.join(UPLOAD_DIR, safe_name)
            with open(dest, "wb") as f:
                f.write(content)
            saved.append(safe_name)
        return ("redirect", "/workspace")
    except Exception as e:
        return ("json", {"error": str(e)})


def render_project_tree():
    projects = list_projects()
    if not projects:
        return '<div class="file-empty">프로젝트 없음</div>'

    STATUS_LABELS = {"active": "진행중", "paused": "보류", "done": "완료"}
    STATUS_COLORS = {"active": "#10b981", "paused": "#f59e0b", "done": "#64748b"}

    html = ""
    for p in projects:
        pid = p["id"].replace('"', '')
        pname = p["name"].replace("&", "&amp;").replace("<", "&lt;")
        color = p["color"]
        status = p.get("status", "active")
        s_color = STATUS_COLORS.get(status, "#64748b")
        s_label = STATUS_LABELS.get(status, status)

        file_items = ""
        for fname in p["files"]:
            if fname == "meta.json":
                continue
            safe = fname.replace("&", "&amp;").replace("<", "&lt;")
            ext = fname.rsplit(".", 1)[-1].lower() if "." in fname else ""
            icons = {"md": "📝", "json": "⚙️", "py": "🐍", "js": "📜", "ts": "📘",
                     "html": "🌐", "css": "🎨", "txt": "📄", "sh": "⚡"}
            icon = icons.get(ext, "📄")
            file_items += f'<div class="tree-file"><span>{icon}</span><span>{safe}</span></div>'

        html += f'''
        <div class="tree-project">
          <div class="tree-project-header" onclick="toggleProject('{pid}')">
            <span class="tree-chevron" id="chev-{pid}">▶</span>
            <span class="tree-dot" style="background:{color}"></span>
            <a href="{DASHBOARD_URL}?project={pid}" target="_blank" class="tree-project-name"
               onclick="event.stopPropagation()">{pname}</a>
            <span class="tree-status" style="color:{s_color}">{s_label}</span>
          </div>
          <div class="tree-files" id="tree-{pid}" style="display:none">
            {file_items if file_items else '<div class="tree-file" style="color:#475569">파일 없음</div>'}
          </div>
        </div>'''
    return html


def render_workspace():
    files = list_files()
    file_rows = ""
    for f in files:
        name = f["name"].replace("&", "&amp;").replace("<", "&lt;")
        file_rows += f'''
        <div class="file-item">
          <span class="file-name" title="{name}">{name}</span>
          <span class="file-meta">{f["size"]} · {f["mtime"]}</span>
          <form method="POST" action="/workspace/delete" style="display:inline">
            <input type="hidden" name="filename" value="{f["name"]}">
            <button class="del-btn" type="submit">✕</button>
          </form>
        </div>'''
    file_empty = '<div class="file-empty">파일 없음</div>' if not file_rows else ""
    project_tree = render_project_tree()

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🖥️ 워크스페이스</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;font-family:-apple-system,sans-serif;background:#0f172a;overflow:hidden}}
nav{{background:#1e293b;padding:10px 20px;display:flex;align-items:center;justify-content:space-between;border-bottom:1px solid #334155;height:48px;flex-shrink:0}}
nav .title{{color:white;font-weight:600;font-size:0.95rem}}
nav a{{color:#94a3b8;text-decoration:none;font-size:0.85rem}}
nav a:hover{{color:white}}
.layout{{display:flex;height:calc(100vh - 48px)}}
.sidebar{{width:280px;background:#1e293b;border-right:1px solid #334155;display:flex;flex-direction:column;flex-shrink:0;overflow:hidden}}
.sidebar-section{{padding:14px;border-bottom:1px solid #334155;flex-shrink:0}}
.sidebar-title{{color:#94a3b8;font-size:0.75rem;font-weight:600;text-transform:uppercase;letter-spacing:0.05em;margin-bottom:10px}}
.drop-zone{{border:1.5px dashed #475569;border-radius:8px;padding:16px 12px;text-align:center;cursor:pointer;transition:all 0.2s;background:#0f172a}}
.drop-zone:hover,.drop-zone.over{{border-color:#0ea5e9;background:#0c1a2e}}
.drop-zone p{{color:#64748b;font-size:0.8rem;margin-bottom:8px}}
.drop-zone input{{display:none}}
.upload-btn{{display:inline-block;padding:6px 14px;background:#0ea5e9;color:white;border-radius:6px;font-size:0.8rem;cursor:pointer;border:none}}
.progress{{display:none;color:#0ea5e9;font-size:0.8rem;margin-top:8px}}
.scroll-section{{overflow-y:auto;flex-shrink:1}}
.uploaded-section{{max-height:160px;border-bottom:1px solid #334155}}
.projects-section{{flex:1;min-height:0}}
.file-list{{padding:8px}}
.file-item{{display:flex;align-items:center;gap:6px;padding:6px 8px;border-radius:6px;margin-bottom:2px}}
.file-item:hover{{background:#0f172a}}
.file-name{{flex:1;color:#e2e8f0;font-size:0.82rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.file-meta{{color:#475569;font-size:0.72rem;white-space:nowrap}}
.del-btn{{background:none;border:none;color:#475569;cursor:pointer;font-size:0.75rem;padding:2px 4px;border-radius:4px}}
.del-btn:hover{{color:#ef4444}}
.file-empty{{color:#475569;font-size:0.82rem;text-align:center;padding:16px}}
/* project tree */
.tree-project{{margin-bottom:2px}}
.tree-project-header{{display:flex;align-items:center;gap:6px;padding:7px 14px;cursor:pointer;transition:background 0.15s}}
.tree-project-header:hover{{background:#0f172a}}
.tree-chevron{{color:#475569;font-size:0.6rem;width:10px;transition:transform 0.2s;flex-shrink:0}}
.tree-dot{{width:8px;height:8px;border-radius:50%;flex-shrink:0}}
.tree-project-name{{flex:1;color:#e2e8f0;font-size:0.82rem;text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.tree-project-name:hover{{color:#0ea5e9}}
.tree-status{{font-size:0.7rem;flex-shrink:0}}
.tree-files{{padding:4px 0 4px 28px;border-left:1px solid #334155;margin-left:20px}}
.tree-file{{display:flex;align-items:center;gap:5px;padding:4px 8px;color:#64748b;font-size:0.78rem;border-radius:4px}}
.tree-file:hover{{color:#94a3b8;background:#0f172a}}
.terminal-area{{flex:1;overflow:hidden}}
iframe{{width:100%;height:100%;border:none;display:block}}
</style>
</head>
<body>
<nav>
  <span class="title">🖥️ 워크스페이스</span>
  <div style="display:flex;align-items:center;gap:16px">
    <a href="{DASHBOARD_URL}" target="_blank" style="color:#0ea5e9;display:flex;align-items:center;gap:5px;font-size:0.85rem">
      <span>📁</span> 프로젝트 대시보드
    </a>
    <a href="/">← 홈</a>
  </div>
</nav>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-section">
      <div class="sidebar-title">파일 업로드</div>
      <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
        <p>드래그하거나 클릭</p>
        <span class="upload-btn">파일 선택</span>
        <input type="file" id="fileInput" multiple>
        <div class="progress" id="progress">업로드 중...</div>
      </div>
    </div>
    <div class="scroll-section uploaded-section">
      <div style="padding:10px 14px 4px">
        <div class="sidebar-title" style="margin-bottom:0">업로드된 파일</div>
      </div>
      <div class="file-list">{file_rows}{file_empty}</div>
    </div>
    <div class="scroll-section projects-section">
      <div style="padding:10px 14px 4px">
        <div class="sidebar-title" style="margin-bottom:0">프로젝트</div>
      </div>
      <div style="padding:6px 0">{project_tree}</div>
    </div>
  </div>
  <div class="terminal-area">
    <iframe src="http://localhost:{TTYD_PORT}" id="terminal" allow="clipboard-read; clipboard-write"></iframe>
  </div>
</div>
<script>
const drop = document.getElementById('dropZone');
const inp = document.getElementById('fileInput');
const progress = document.getElementById('progress');

drop.addEventListener('dragover', e => {{ e.preventDefault(); drop.classList.add('over'); }});
drop.addEventListener('dragleave', () => drop.classList.remove('over'));
drop.addEventListener('drop', e => {{ e.preventDefault(); drop.classList.remove('over'); uploadFiles(e.dataTransfer.files); }});
inp.addEventListener('change', () => uploadFiles(inp.files));

async function uploadFiles(files) {{
  if (!files.length) return;
  progress.style.display = 'block';
  for (const file of files) {{
    const fd = new FormData();
    fd.append('file', file);
    await fetch('/workspace/upload', {{method:'POST', body:fd}});
  }}
  location.reload();
}}

function toggleProject(id) {{
  const tree = document.getElementById('tree-' + id);
  const chev = document.getElementById('chev-' + id);
  if (tree.style.display === 'none') {{
    tree.style.display = 'block';
    chev.style.transform = 'rotate(90deg)';
  }} else {{
    tree.style.display = 'none';
    chev.style.transform = '';
  }}
}}
</script>
</body>
</html>'''
