# Receipt Ledger — 아키텍처 설계

**작성**: 민준 (아키텍트)  
**날짜**: 2026-05-29  
**참조**: `docs/receipt_ledger_design.md` (수아의 UI 시안)  
**상태**: 설계 완료, 구현 대기

---

## 1. 데이터 모델 — Ledger JSON 스키마 (v2)

**파일**: `~/.appdata/cardconv/receipts_{username}.json`  
(기존 파일 경로 유지, 스키마 확장)

```json
{
  "version": 2,
  "last_batch_at": "2026-05-29T09:00:00",
  "entries": [
    {
      "id": "rcpt_a1b2c3d4",
      "file_id": "1BxiMVs0XRA5nFMdKvBdBZjgmUGDerty",
      "filename": "receipt_20260528.jpg",
      "drive_url": "https://drive.google.com/file/d/.../view",
      "mime_type": "image/jpeg",

      "ocr_status": "done",
      "ocr_date": "2026-05-28",
      "ocr_amount": 42.50,
      "ocr_merchant": "STARBUCKS SF",

      "match_status": "matched",
      "matched_at": "2026-05-29T14:22:11",
      "matched_transaction": {
        "date": "2026-05-28",
        "amount": 42.50,
        "vendor": "STARBUCKS"
      },

      "synced_at": "2026-05-29T09:01:44",
      "uploaded_at": "2026-05-28T18:30:00"
    }
  ]
}
```

### 필드 정의

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | str | `rcpt_` + uuid4()[:8] |
| `file_id` | str | Google Drive file ID |
| `ocr_status` | enum | `pending` \| `done` \| `failed` |
| `ocr_date` | str\|null | YYYY-MM-DD |
| `ocr_amount` | float\|null | 금액 |
| `ocr_merchant` | str\|null | 가맹점명 |
| `match_status` | enum | `unmatched` \| `matched` \| `pending_ocr` |
| `matched_at` | str\|null | ISO 8601 |
| `matched_transaction` | obj\|null | 매칭된 CSV 거래 |
| `synced_at` | str | Drive 감지 시각 |
| `uploaded_at` | str | 업로드/최초 감지 시각 |

### 마이그레이션 (v1 → v2)

기존 `receipts_{username}.json`은 배열 형식 (v1). `_load_ledger()` 최초 호출 시 자동 변환:

```python
# v1: [{"file_id": ..., "matched": true, ...}, ...]
# v2: {"version": 2, "entries": [...]}
```

변환 규칙:
- 배열이면 `{"version": 2, "last_batch_at": null, "entries": 배열}`로 래핑
- 각 entry에 `id` 없으면 `"rcpt_" + (file_id or "")[:8]` 생성
- `matched: True` → `match_status: "matched"`
- `ocr_amount is None` → `ocr_status: "pending"` / 있으면 `"done"`

---

## 2. URL 구조

| Method | Path | 역할 |
|--------|------|------|
| GET | `/cardconv` | 기존 메인 (유지) |
| **GET** | **`/cardconv/ledger`** | Ledger 페이지 (수아 UI 기준) |
| **GET** | **`/cardconv/ledger/api`** | Ledger JSON API |
| **POST** | **`/cardconv/ledger/<id>/status`** | 수동 상태 변경 |
| **GET** | **`/cardconv/receipts/image/<file_id>`** | Drive 이미지 프록시 |
| **POST** | **`/cardconv/batch/run`** | Manual Batch OCR trigger |
| POST | `/cardconv/drive/sync` | 기존 수동 Sync (유지) |
| POST | `/cardconv/upload` | 기존 CSV 업로드 + Cross-check (유지) |

**굵게** 표시된 것이 신규 엔드포인트.

### Ledger API 쿼리 파라미터

```
GET /cardconv/ledger/api?status=all&from=2026-05-01&to=2026-05-31&page=1&limit=50
```

응답:
```json
{
  "total": 24,
  "matched": 21,
  "unmatched": 3,
  "pending_ocr": 0,
  "page": 1,
  "pages": 1,
  "entries": [...]
}
```

### 상태 변경 API

```
POST /cardconv/ledger/<id>/status
body: status=matched | status=unmatched | status=pending_ocr
```

응답: `{"ok": true}` or `{"error": "..."}` (JSON)

---

## 3. Daily Batch OCR 실행 방식

### 결정: 시스템 cron + HTTP trigger

```
[cron 09:00] → curl POST /cardconv/batch/run -H "X-Batch-Secret: <secret>"
                     ↓
               [_run_batch_ocr(username)]
                     ↓
               Drive scan → 신규 파일 감지 → Claude Vision OCR
                     ↓
               Ledger 업데이트 → last_batch_at 갱신
```

**인증**: `X-Batch-Secret` 헤더. `.env`에 `CARDCONV_BATCH_SECRET=<random>` 추가.  
세션 쿠키 불필요 — cron에서 쿠키 관리하기 어려움.

```bash
# crontab 등록 예시
0 9 * * * curl -s -X POST http://localhost:8080/cardconv/batch/run \
  -H "X-Batch-Secret: ${CARDCONV_BATCH_SECRET}" \
  >> /tmp/cardconv_batch.log 2>&1
```

**방식 비교**:

| 방식 | 장점 | 단점 | 결론 |
|------|------|------|------|
| 시스템 cron + curl | 단순, 재시작 후 자동 | crontab 수동 등록 | **채택** |
| Python threading.Timer | 외부 설정 불필요 | 서버 재시작 시 초기화 | 부적합 |
| CronCreate MCP | 팀 내 통합 | 서버 상태 의존 | 추후 고려 |

**Batch 처리 로직**:
1. `jongha.kang` 유저로 Drive 스캔
2. `ocr_status == "pending"` 또는 Ledger에 없는 신규 파일 감지
3. Claude Vision OCR (`_ocr_receipt` 재사용)
4. Ledger entry 업데이트 (`ocr_status: "done"`, date/amount/merchant)
5. `last_batch_at` 갱신
6. 결과: `{"processed": N, "failed": M, "total": T}` JSON 반환

---

## 4. 기존 cardconv.py와의 통합 결정

### 결정: cardconv.py 내 통합 (Ledger 섹션 추가)

**이유**:
- Drive OAuth, OCR, 영수증 로직이 이미 cardconv.py에 집중
- 별도 파일 분리 시 Drive util 코드 중복 또는 circular import
- `# ── Ledger ──` 섹션으로 명확히 구분하면 가독성 유지 가능

**신규 함수 추가 위치** (handle() 함수 위):

```python
# ── Ledger ────────────────────────────────────────────────────────────

def _load_ledger(username: str) -> dict:
    """Load ledger, auto-migrating v1 (list) to v2 (dict) format."""

def _save_ledger(username: str, ledger: dict):
    """Persist ledger to disk."""

def _ledger_entries(username: str) -> list:
    """Return entries list from ledger."""

def _ledger_stats(entries: list) -> dict:
    """Return {total, matched, unmatched, pending_ocr}."""

def _run_batch_ocr(username: str) -> dict:
    """Scan Drive, OCR pending files, update ledger. Returns stats."""
```

**기존 함수 변경**:
- `_load_receipts()` / `_save_receipts()` → `_load_ledger()` / `_save_ledger()` 내부 호출로 교체
- `convert()` 내 매칭 후 `receipt_match['matched'] = True` → `receipt_match['match_status'] = 'matched'` 로 변경

---

## 5. 이미지 서빙 방식

### Drive API 프록시

```
Browser
  → GET /cardconv/receipts/image/<file_id>
  → [cardconv.py] Drive API files().get_media(fileId)
  → binary bytes
  → HTTP Response (Content-Type: image/jpeg | image/png | application/pdf)
```

**구현 스케치**:
```python
def _handle_image_proxy(username: str, file_id: str):
    service = _get_drive_service(username)
    if not service:
        return ("html", "<p>Drive not connected</p>", 401)
    try:
        meta    = service.files().get(fileId=file_id, fields="mimeType").execute()
        mime    = meta.get("mimeType", "image/jpeg")
        content = service.files().get_media(fileId=file_id).execute()
        # ("binary", bytes, mime, filename_or_None)
        # filename=None → Content-Disposition: inline
        return ("binary", content, mime, None)
    except Exception as e:
        return ("html", f"<p>Image load error: {e}</p>", 404)
```

**server.py 지원 확인 필요**: `("binary", bytes, mime, None)` → `Content-Disposition: inline` 처리 필요.  
현재 `("file", path, mime, filename)` 은 attachment 다운로드. inline 버전 추가 필요.

**썸네일 (목록 테이블용)**:
```html
<!-- Drive 썸네일 URL — 인증 없이 접근 가능 (로그인된 Google 계정 기준) -->
<img src="https://drive.google.com/thumbnail?id=FILE_ID&sz=w80" class="receipt-thumb">
```
Ledger 뷰에서 썸네일은 이 URL 사용. 클릭 시 `/cardconv/receipts/image/<file_id>` 로 원본.

> **주의**: Drive thumbnail URL은 Google 로그인 세션 필요. 사용자가 브라우저에서 Google에 로그인되어 있다면 동작. 미로그인 시 → 프록시 URL로 fallback.

---

## 6. CSV Cross-check 개선

기존 `convert()` 내 매칭 로직에서 상태 업데이트 방식만 변경:

```python
# 기존
receipt_match['matched'] = True
receipt_match['matched_transaction'] = {...}

# 변경
receipt_match['match_status'] = 'matched'
receipt_match['matched_at'] = datetime.now().isoformat()
receipt_match['matched_transaction'] = {...}
```

xlsx column 27 표시는 변경 없음.

---

## 7. server.py 변경 필요 사항

```python
# 신규 응답 타입 추가
elif resp_type == "binary":
    content, mime, filename = resp[1], resp[2], resp[3]
    self.send_response(200)
    self.send_header("Content-Type", mime)
    if filename:
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
    else:
        self.send_header("Content-Disposition", "inline")
    self.send_header("Content-Length", str(len(content)))
    self.end_headers()
    self.wfile.write(content)
```

---

## 8. 구현 체크리스트 (지훈에게)

### Phase 1 — 데이터 마이그레이션 (우선)
- [ ] `_load_ledger()` — v1 자동 마이그레이션 포함
- [ ] `_save_ledger()` / `_ledger_entries()` / `_ledger_stats()`
- [ ] 기존 `_load_receipts()` / `_save_receipts()` 호출을 ledger 함수로 교체
- [ ] `convert()` 내 `matched: True` → `match_status: "matched"` 변경

### Phase 2 — Batch OCR
- [ ] `_run_batch_ocr(username)` 구현
- [ ] `POST /cardconv/batch/run` 엔드포인트 (X-Batch-Secret 인증)
- [ ] `.env`에 `CARDCONV_BATCH_SECRET` 추가

### Phase 3 — Ledger API
- [ ] `GET /cardconv/ledger/api` JSON API
- [ ] `POST /cardconv/ledger/<id>/status` 상태 변경 API

### Phase 4 — Ledger View
- [ ] `GET /cardconv/ledger` → `_render_ledger()` 구현
- [ ] 수아의 UI 시안 (`docs/receipt_ledger_design.md`) 기준으로 HTML/CSS 구현
- [ ] 탭 바 통합 (변환 / 영수증 원장 / 키워드) — URL hash 방식

### Phase 5 — 이미지 서빙
- [ ] server.py에 `binary` inline 응답 타입 추가
- [ ] `GET /cardconv/receipts/image/<file_id>` 엔드포인트
- [ ] Drive thumbnail URL → img 태그 (목록), 프록시 URL → 슬라이드오버 상세

### Phase 6 — Cron 설정
- [ ] crontab 등록
- [ ] smoke-test.sh에 `/cardconv/ledger/api` 항목 추가

---

## 9. 의존성

추가 패키지 없음. 기존 의존성으로 모두 구현 가능:
- `google-api-python-client` — Drive API
- `anthropic` — Claude Vision OCR
- `openpyxl` — xlsx
- 내장: `uuid`, `datetime`, `json`, `base64`
