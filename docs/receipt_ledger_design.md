# Receipt Ledger UI 시안

**작성**: 수아 (UI/UX)
**날짜**: 2026-05-29
**기준**: Wayfinder 다크 테마 (`--surface #111827`, `--accent #38bdf8`)

---

## 1. 탭 통합 구조

기존 `/cardconv` 페이지 상단에 탭 바를 추가합니다.

```
┌─────────────────────────────────────────────────────────────────┐
│ 💳 Card Converter                               👤 user · Logout│
├─────────────────────────────────────────────────────────────────┤
│  [ 변환 ]  [ 영수증 원장 ●3 ]  [ 키워드 ]                       │
│  ─────────                                                       │
└─────────────────────────────────────────────────────────────────┘
```

- 활성 탭: 하단 `--accent` 색 밑줄 + 텍스트 밝게
- `●3` 배지: 미매칭 영수증 수 (빨간 dot)
- 탭 전환은 URL hash 방식 (`#convert`, `#ledger`, `#keywords`) — 서버 왕복 없음

---

## 2. 탭 1: 변환 (기존 유지)

현재 구조 그대로. 탭 바만 추가.

---

## 3. 탭 2: 영수증 원장 (신규)

### 3-1. 상단 통계 바

```
┌────────────────────────────────────────────────────────────────┐
│  📊 이번 달 현황                                                │
│                                                                │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐         │
│  │   총 영수증   │  │    매칭됨    │  │   미매칭     │         │
│  │      24      │  │      21  ✅  │  │    3    ❌   │         │
│  └──────────────┘  └──────────────┘  └──────────────┘         │
└────────────────────────────────────────────────────────────────┘
```

### 3-2. 필터 바

```
┌────────────────────────────────────────────────────────────────┐
│  📅 [2026-05-01] ~ [2026-05-31]   상태: [전체 ▼]   [초기화]   │
└────────────────────────────────────────────────────────────────┘
```

### 3-3. 영수증 목록 테이블

```
┌────────────────────────────────────────────────────────────────────────────┐
│  날짜        금액         가맹점명             썸네일    CSV 매칭   상태    │
├────────────────────────────────────────────────────────────────────────────┤
│  2026-05-28  $  45.20    STARBUCKS #1234      [🖼]      $45.20    ✅ 매칭  │
│  2026-05-27  $  128.50   SWEETGREEN SOMA      [🖼]      $128.50   ✅ 매칭  │
│  2026-05-26  $   23.00   DOORDASH*ORDER       [🖼]      -         ❌ 미매칭│
│  2026-05-25  $  312.00   HYATT REGENCY        [🖼]      $312.00   ✅ 매칭  │
│  2026-05-24  $   18.75   UNKNOWN MERCHANT     [🖼]      -         ⏳ 검토중│
├────────────────────────────────────────────────────────────────────────────┤
│                                       [이전]  1 / 3  [다음]               │
└────────────────────────────────────────────────────────────────────────────┘
```

**행 인터랙션**:
- 행 클릭 → 상세 슬라이드오버 (오른쪽에서 패널이 밀려 들어옴)
- 썸네일 `[🖼]`: 실제 영수증 이미지 미리보기 (hover 시 툴팁 팝업, 60×60px)
- 상태 배지 컬러: ✅ `#22c55e`, ❌ `#ef4444`, ⏳ `#f59e0b`

---

## 4. 탭 2: 상세 뷰 — 슬라이드오버 패널

행 클릭 시 오른쪽에서 슬라이드인. 메인 목록은 반투명 오버레이로 어두워짐.

```
┌───────────────────────────────────────────────────────────────────┐
│ 메인 목록 (어두워짐)         │ ┌───────────────────────────────┐ │
│                              │ │  × 닫기                        │ │
│                              │ │                                │ │
│                              │ │  ─── 영수증 이미지 ───         │ │
│                              │ │  ┌─────────────────────┐      │ │
│                              │ │  │                     │      │ │
│                              │ │  │   [영수증 사진]      │      │ │
│                              │ │  │   Drive에서 로드     │      │ │
│                              │ │  │                     │      │ │
│                              │ │  └─────────────────────┘      │ │
│                              │ │                                │ │
│                              │ │  ─── OCR 결과 ───             │ │
│                              │ │  날짜    2026-05-28            │ │
│                              │ │  금액    $ 45.20               │ │
│                              │ │  가맹점  STARBUCKS #1234       │ │
│                              │ │                                │ │
│                              │ │  ─── CSV 매칭 거래 ───        │ │
│                              │ │  날짜    2026-05-28            │ │
│                              │ │  금액    $ 45.20               │ │
│                              │ │  설명    STARBUCKS #1234 CA    │ │
│                              │ │  카테고리 Coffee, Snack        │ │
│                              │ │                                │ │
│                              │ │  상태: ✅ 매칭됨               │ │
│                              │ │                                │ │
│                              │ │  [❌ 미매칭으로 변경]           │ │
│                              │ │  [⏳ 검토 필요로 변경]          │ │
│                              │ └───────────────────────────────┘ │
└───────────────────────────────────────────────────────────────────┘
```

---

## 5. 탭 3: 키워드 (기존 유지)

현재 구조 그대로. 탭 바만 추가.

---

## 6. CSS 스케치

```css
/* ── 탭 바 ──────────────────────────────────────── */
.tab-bar {
  display: flex;
  gap: 0;
  border-bottom: 1px solid var(--border);
  margin-bottom: 20px;
}
.tab-item {
  padding: 10px 20px;
  font-size: .82rem;
  font-weight: 600;
  color: var(--text-muted);
  cursor: pointer;
  border-bottom: 2px solid transparent;
  transition: color .15s, border-color .15s;
  position: relative;
}
.tab-item:hover { color: var(--text); }
.tab-item.active {
  color: var(--accent);
  border-bottom-color: var(--accent);
}
.tab-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 16px; height: 16px;
  background: #ef4444;
  border-radius: 50%;
  font-size: .65rem;
  font-weight: 700;
  color: #fff;
  margin-left: 5px;
  vertical-align: middle;
}

/* ── 통계 카드 ───────────────────────────────────── */
.stat-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 12px;
  margin-bottom: 16px;
}
.stat-card {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  text-align: center;
}
.stat-value {
  font-size: 1.6rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.2;
}
.stat-label {
  font-size: .73rem;
  color: var(--text-muted);
  margin-top: 4px;
  text-transform: uppercase;
  letter-spacing: .06em;
}

/* ── 필터 바 ─────────────────────────────────────── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  margin-bottom: 14px;
  flex-wrap: wrap;
}
.filter-bar input[type="date"],
.filter-bar select {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  font-size: .82rem;
  padding: 5px 8px;
  outline: none;
}
.filter-bar input[type="date"]:focus,
.filter-bar select:focus {
  border-color: var(--accent);
}

/* ── 원장 테이블 ──────────────────────────────────── */
.ledger-table {
  width: 100%;
  border-collapse: collapse;
  font-size: .83rem;
}
.ledger-table th {
  padding: 8px 12px;
  text-align: left;
  font-size: .72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .07em;
  color: var(--text-muted);
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--surface);
}
.ledger-table td {
  padding: 10px 12px;
  border-bottom: 1px solid var(--border);
  vertical-align: middle;
}
.ledger-table tr:hover td { background: var(--surface-2); cursor: pointer; }
.ledger-table tr:last-child td { border-bottom: none; }

/* 썸네일 */
.receipt-thumb {
  width: 40px; height: 40px;
  border-radius: 6px;
  object-fit: cover;
  border: 1px solid var(--border);
  background: var(--surface-3);
  cursor: zoom-in;
}
.receipt-thumb-placeholder {
  width: 40px; height: 40px;
  border-radius: 6px;
  border: 1px dashed var(--border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: .75rem;
  color: var(--text-muted);
}

/* 상태 배지 */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: .72rem;
  font-weight: 700;
  white-space: nowrap;
}
.status-matched   { background: rgba(34,197,94,.15);  color: #22c55e; }
.status-unmatched { background: rgba(239,68,68,.15);  color: #ef4444; }
.status-pending   { background: rgba(245,158,11,.15); color: #f59e0b; }

/* ── 슬라이드오버 패널 ────────────────────────────── */
.overlay-bg {
  position: fixed; inset: 0;
  background: rgba(0,0,0,.55);
  z-index: 100;
  opacity: 0;
  pointer-events: none;
  transition: opacity .2s;
}
.overlay-bg.open { opacity: 1; pointer-events: all; }

.detail-panel {
  position: fixed;
  top: 0; right: 0;
  width: 420px; max-width: 100vw;
  height: 100vh;
  background: var(--surface);
  border-left: 1px solid var(--border);
  z-index: 101;
  transform: translateX(100%);
  transition: transform .25s cubic-bezier(.4,0,.2,1);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}
.detail-panel.open { transform: translateX(0); }

.detail-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
  position: sticky;
  top: 0;
  background: var(--surface);
}
.detail-section {
  padding: 16px 20px;
  border-bottom: 1px solid var(--border);
}
.detail-section-title {
  font-size: .7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: .08em;
  color: var(--text-muted);
  margin-bottom: 10px;
}
.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: .84rem;
  padding: 4px 0;
}
.detail-row .key { color: var(--text-muted); }
.detail-row .val { font-weight: 600; color: var(--text); }

.receipt-image-full {
  width: 100%;
  border-radius: var(--radius-md);
  border: 1px solid var(--border);
  object-fit: contain;
  max-height: 260px;
}

.detail-actions {
  padding: 16px 20px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: auto;
}

/* ── 페이지네이션 ─────────────────────────────────── */
.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  padding: 14px;
  font-size: .82rem;
  color: var(--text-muted);
}
.pagination button {
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 6px;
  color: var(--text);
  padding: 4px 12px;
  font-size: .8rem;
  cursor: pointer;
}
.pagination button:disabled { opacity: .4; cursor: default; }
```

---

## 7. 인터랙션 플로우

```
사용자 흐름:
  [원장 탭 클릭]
       │
       ▼
  [통계 + 필터 + 테이블 로드]
       │
       ├─ [행 클릭] ─────→ [슬라이드오버 열림]
       │                         │
       │                         ├─ 영수증 이미지 로드 (Drive)
       │                         ├─ OCR 결과 표시
       │                         ├─ CSV 매칭 정보 표시
       │                         └─ [상태 변경 버튼] → POST → 행 상태 갱신
       │
       ├─ [필터 변경] ──→ [테이블 재로드] (GET params)
       │
       └─ [페이지 이동] → [테이블 재로드]
```

---

## 8. 반응형 고려사항

- `max-width: 860px` 컨테이너 유지 (기존과 동일)
- 모바일(<600px): 테이블 가로 스크롤, 슬라이드오버 전체화면(`width:100vw`)
- 통계 카드: 모바일에서 `grid-template-columns: 1fr 1fr` → 미매칭 단독 행

---

## 9. 구현 노트 (지훈에게)

| 항목 | 방식 |
|------|------|
| 탭 전환 | URL hash (`location.hash`) + `hashchange` 이벤트. 탭별 섹션 show/hide |
| 원장 데이터 API | `GET /cardconv/ledger?from=&to=&status=&page=` → JSON |
| 상태 변경 API | `POST /cardconv/ledger/<id>/status` body: `{status: "matched"\|"unmatched"\|"pending"}` |
| 영수증 이미지 | `GET /cardconv/receipt/<id>/image` → Drive 파일 proxy (base64 or redirect) |
| 슬라이드오버 | 순수 JS. 외부 클릭(`overlay-bg`) 또는 Esc 키로 닫힘 |
| 필터 초기값 | 이번 달 1일 ~ 오늘 (JS로 자동 세팅) |
