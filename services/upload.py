import os, json, re
from datetime import datetime

META = {
    "name": "파일 업로드",
    "path": "/upload",
    "icon": "📁",
    "description": "파일 올리기",
    "hidden": True,
}

UPLOAD_DIR = os.path.expanduser("~/uploads")


def _ensure_dir():
    os.makedirs(UPLOAD_DIR, exist_ok=True)


def list_files():
    _ensure_dir()
    files = []
    for f in sorted(os.listdir(UPLOAD_DIR), reverse=True):
        path = os.path.join(UPLOAD_DIR, f)
        if os.path.isfile(path):
            size = os.path.getsize(path)
            mtime = datetime.fromtimestamp(os.path.getmtime(path))
            files.append({"name": f, "size": size, "mtime": mtime.strftime("%Y-%m-%d %H:%M")})
    return files


def handle(method, path, body, ctx):
    _ensure_dir()

    if method == "GET" and path == "/upload":
        return ("html", render_upload())

    if method == "POST" and path == "/upload":
        # body is raw handler — handled specially via server raw_handler
        raw = body.get("__raw__")
        if raw:
            return handle_upload(raw)
        return ("json", {"error": "업로드 데이터 없음"})

    if method == "POST" and path == "/upload/delete":
        fname = body.get("filename", "")
        if isinstance(fname, list):
            fname = fname[0] if fname else ""
        if fname and ".." not in fname:
            fpath = os.path.join(UPLOAD_DIR, fname)
            if os.path.exists(fpath):
                os.remove(fpath)
        return ("redirect", "/upload")

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
        parts = data.split(boundary)
        for part in parts:
            if b'filename="' not in part:
                continue
            fname_m = re.search(rb'filename="([^"]+)"', part)
            if not fname_m:
                continue
            safe_name = os.path.basename(fname_m.group(1).decode())
            # Skip headers (blank line \r\n\r\n separates headers from content)
            header_end = part.find(b"\r\n\r\n")
            if header_end == -1:
                continue
            content = part[header_end + 4:]
            if content.endswith(b"\r\n"):
                content = content[:-2]
            dest = os.path.join(UPLOAD_DIR, safe_name)
            with open(dest, "wb") as f:
                f.write(content)
        return ("redirect", "/upload")
    except Exception as e:
        return ("json", {"error": str(e)})


def render_upload():
    files = list_files()

    rows = ""
    for f in files:
        size_str = f"{f['size']:,} bytes" if f["size"] < 1024 else f"{f['size']//1024:,} KB"
        rows += f'''
        <tr>
          <td>{f["name"]}</td>
          <td style="color:#64748b;font-size:0.85rem">{size_str}</td>
          <td style="color:#64748b;font-size:0.85rem">{f["mtime"]}</td>
          <td>
            <form method="POST" action="/upload/delete" style="display:inline">
              <input type="hidden" name="filename" value="{f["name"]}">
              <button type="submit" style="background:#fee2e2;color:#dc2626;border:none;padding:3px 10px;border-radius:6px;cursor:pointer;font-size:0.8rem">삭제</button>
            </form>
          </td>
        </tr>'''

    empty = "" if rows else '<tr><td colspan="4" style="text-align:center;color:#94a3b8;padding:40px">업로드된 파일이 없습니다</td></tr>'

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📁 파일 업로드</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,sans-serif;background:#f5f5f5;min-height:100vh}}
nav{{background:#1e293b;padding:12px 24px;display:flex;align-items:center;justify-content:space-between}}
nav span{{color:white;font-weight:600}}
nav a{{color:#94a3b8;text-decoration:none;font-size:0.85rem}}
nav a:hover{{color:white}}
.container{{max-width:700px;margin:40px auto;padding:0 16px}}
h1{{font-size:1.5rem;color:#1a1a1a;margin-bottom:24px}}
.drop-zone{{border:2px dashed #cbd5e1;border-radius:12px;padding:48px;text-align:center;background:white;cursor:pointer;transition:all 0.2s;margin-bottom:24px}}
.drop-zone:hover,.drop-zone.dragover{{border-color:#0ea5e9;background:#f0f9ff}}
.drop-zone p{{color:#64748b;margin-bottom:12px}}
.drop-zone input{{display:none}}
.upload-btn{{display:inline-block;padding:10px 24px;background:#0ea5e9;color:white;border-radius:8px;cursor:pointer;font-size:0.95rem;border:none}}
table{{width:100%;border-collapse:collapse;background:white;border-radius:12px;overflow:hidden;border:1px solid #e2e8f0}}
th{{background:#f8fafc;padding:12px 16px;text-align:left;font-size:0.85rem;color:#64748b;border-bottom:1px solid #e2e8f0}}
td{{padding:12px 16px;border-bottom:1px solid #f1f5f9;font-size:0.9rem}}
tr:last-child td{{border-bottom:none}}
.progress{{display:none;margin-top:12px;color:#0ea5e9;font-size:0.9rem}}
</style>
</head>
<body>
<nav>
  <span>📁 파일 업로드</span>
  <a href="/">← 홈</a>
</nav>
<div class="container">
  <h1>파일 업로드</h1>
  <div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
    <p>파일을 드래그하거나 클릭해서 업로드</p>
    <label class="upload-btn">파일 선택</label>
    <input type="file" id="fileInput" multiple>
    <div class="progress" id="progress">업로드 중...</div>
  </div>
  <table>
    <thead><tr><th>파일명</th><th>크기</th><th>날짜</th><th></th></tr></thead>
    <tbody>{rows}{empty}</tbody>
  </table>
</div>
<script>
const drop = document.getElementById('dropZone');
const inp = document.getElementById('fileInput');
const progress = document.getElementById('progress');

drop.addEventListener('dragover', e => {{ e.preventDefault(); drop.classList.add('dragover'); }});
drop.addEventListener('dragleave', () => drop.classList.remove('dragover'));
drop.addEventListener('drop', e => {{
  e.preventDefault();
  drop.classList.remove('dragover');
  uploadFiles(e.dataTransfer.files);
}});
inp.addEventListener('change', () => uploadFiles(inp.files));

async function uploadFiles(files) {{
  if (!files.length) return;
  progress.style.display = 'block';
  for (const file of files) {{
    const fd = new FormData();
    fd.append('file', file);
    await fetch('/upload', {{method:'POST', body:fd}});
  }}
  location.reload();
}}
</script>
</body>
</html>'''
