# 법인카드 정산 자동화 프로세스

> 작성일: 2026-05-29  
> 담당: Wayfinder Card Converter (`/cardconv`)

---

## 1. 개요

미국 법인카드(AmEx) 사용 내역을 SAP 업로드 형식으로 자동 변환하고,
영수증 증빙을 Google Drive에 보관하며 거래내역과 자동 매칭하는 시스템.

**처리 대상 카드 소유자:** JONG KANG, JONGHA KANG

---

## 2. 전체 플로우

```
AmEx 포털
    │
    ▼ CSV 다운로드 (매달)
DRM 해제 (Windows)
    │
    ▼
Wayfinder /cardconv
    ├─── CSV 업로드 ──────────────────────────────────────────┐
    │                                                         │
    │         영수증 수집                                      │
    │    폰 사진 / 스캔                                        │
    │         │                                               │
    │    Google Drive                                         │
    │    Wayfinder/Receipts/                                  │
    │         │                                               │
    │    Sync from Drive                                      │
    │    (Claude Vision OCR)                                  │
    │         │                                               │
    │    receipts_user.json                                   │
    │         │                                               │
    └─────────┴──── Convert ───────────────────────────────▶ xlsx
                                                              │
                                                    27번 컬럼 ✅/❌
                                                              │
                                                    매칭 영수증 → Matched/
                                                              │
                                                         SAP 업로드
```

---

## 3. 단계별 상세 프로세스

### STEP 1. AmEx CSV 다운로드

- **주기:** 매달 1회 (정산 마감일 기준)
- **경로:** AmEx 포털 → 내역 내보내기 → CSV
- **주의:** 파일이 **NASCA DRM 암호화** 상태로 다운로드됨
- **필수:** Windows에서 파일 열기 → 다른 이름으로 저장 → 일반 CSV로 저장
- **결과 파일명 예시:** `Posted_2026-05-28.csv`

**CSV 주요 컬럼:**

| 컬럼 | 설명 |
|------|------|
| Date | 거래 날짜 (YYYY-MM-DD) |
| Card Member Name | 카드 소유자명 |
| Amount | 거래 금액 (USD) |
| Merchant Name | 가맹점명 |
| Merchant Doing Business As | 가맹점 영업명 (DBA) |
| Account Number | 카드 번호 (15자리) |

---

### STEP 2. 영수증 수집

영수증을 Google Drive에 업로드한다. **두 가지 방법** 중 선택.

**방법 A — Google Drive에 직접 업로드 (권장)**
1. 스마트폰 카메라로 영수증 촬영
2. Google Drive 앱 열기
3. `Wayfinder/Receipts/` 폴더에 업로드
4. 나중에 Wayfinder에서 Sync 버튼으로 일괄 처리

**방법 B — Wayfinder UI에서 업로드**
1. `/cardconv` 접속
2. Receipts 섹션 → 파일 드래그 앤 드롭
3. 업로드 즉시 OCR 자동 실행

**지원 파일 형식:** JPG, PNG, PDF, GIF, WEBP

**Drive 폴더 구조:**
```
Wayfinder/
└── Receipts/           ← 업로드 폴더 (처리 대기)
    └── Matched/        ← 매칭 완료된 영수증 자동 이동
```

---

### STEP 3. OCR 처리 (Claude Vision)

Drive에 직접 올린 영수증은 **Sync from Drive** 버튼으로 일괄 처리.

**처리 순서:**
1. `/cardconv` → Drive 상태 섹션 → **🔄 Sync from Drive** 클릭
2. `Wayfinder/Receipts/` 폴더 스캔
3. OCR 미완료 파일 감지 (amount = None인 항목)
4. Claude Vision API로 각 파일에서 추출:
   - `date`: 영수증 날짜 (YYYY-MM-DD)
   - `amount`: 총 금액 (숫자)
   - `merchant`: 가맹점명
5. 결과를 `receipts_jongha.kang.json`에 저장

**현재 OCR 한계:**
- 날짜 인식 실패율이 높음 (영수증 포맷마다 다름)
- 날짜 미인식 시 금액+가맹점명으로 fallback 매칭

---

### STEP 4. CSV 변환 (핵심)

**접속:** `/cardconv` → Upload CSV 섹션

**처리 순서:**
1. DRM 해제된 `Posted_*.csv` 파일 드래그 업로드
2. **Convert & Download** 클릭
3. 내부 처리:

```
CSV 파싱
    │
    ├── 필터링: JONG KANG, JONGHA KANG 만 추출 (약 330건)
    │
    ├── 키워드 매칭 → G/L Account 자동 분류
    │   ├── 매칭됨: STARBUCKS → 53410177 (Coffee, Snack and meal)
    │   ├── 매칭됨: UBER → 53270377 (Uber travel)
    │   └── 미매칭: 기본값 53410177 (Coffee, Snack and meal)
    │
    ├── 영수증 매칭 (receipts_user.json 기준)
    │   ├── 1순위: 날짜 + 금액 일치 (±$0.01)
    │   ├── 2순위: 금액 + 가맹점명 (OCR merchant vs CSV vendor)
    │   └── 3순위: 금액만 (날짜/가맹점 없을 때 fallback)
    │
    └── xlsx 생성 (26컬럼 SAP 포맷 + 27번째 영수증 상태)
```

**출력 xlsx 컬럼 구조 (주요):**

| 컬럼 | 내용 |
|------|------|
| 1 | Receipt Type (D) |
| 2 | Employee ID (20170321) |
| 5 | Invoice Date (거래일) |
| 7 | Vendor Name |
| 9 | G/L Account |
| 14 | Gross Doc Amount (금액) |
| 15 | Cost Center (AG010238) |
| 18 | Purpose (자동 분류) |
| 20 | 마스킹된 카드번호 |
| 27 | 영수증 매칭 상태 ✅/❌ |

---

### STEP 5. 결과 검토 및 후처리

다운로드된 xlsx를 Excel에서 열어 확인:

1. **27번 컬럼 확인**
   - `✅ 파일명.jpg` → 영수증 매칭됨, Drive Matched/ 폴더로 자동 이동
   - `❌ Missing` → 영수증 없음, 수동 처리 필요

2. **키워드 미매칭 건 처리**
   - G/L Account 기본값(53410177)으로 채워진 항목 검토
   - 올바른 계정으로 수동 수정
   - `/cardconv` → Keywords 섹션에서 새 키워드 추가 → 다음 달 자동 처리

3. **SAP 업로드**
   - 검토 완료된 xlsx → SAP 시스템에 업로드

---

## 4. 키워드 관리

G/L Account 자동 분류 기준. `/cardconv` → Keywords 섹션에서 관리.

**주요 G/L Account:**

| G/L | Ser. | 용도 |
|-----|------|------|
| 53410177 | 160 | 식사, 커피, 간식 |
| 53210177 | 021 | 사무용품, 유틸리티 |
| 53270377 | 306 | 교통 (Uber, 주차, 항공, 호텔) |
| 53410103 | 159 | 접대 (와인 등) |
| 53311577 | 085 | AI 구독 (OpenAI, Claude 등) |
| 53290177 | 052 | 네트워크 인프라 |
| 53470177 | 289 | 고급 접대 |

---

## 5. 고정값 (변경 불필요)

| 필드 | 값 |
|------|----|
| Receipt Type | D |
| Employee ID | 20170321 |
| Payee | A0016672 |
| Domestic/Overseas | D |
| Currency | USD |
| Tax Code | VV |
| Cost Center | AG010238 |

---

## 6. 현재 알려진 한계점

1. **DRM 해제 수동 필요** — 기업 보안 정책상 자동화 불가
2. **OCR 날짜 인식 불안정** — 파일명 날짜 활용으로 보완 가능
3. **같은 금액 여러 건 오매칭 가능** — 날짜 정보 없을 때 발생
4. **미매칭 건 사유 기록 없음** — 영수증 분실/소액 처리 근거 없음
5. **수동 Sync 필요** — Drive 직접 업로드 시 Sync 버튼 눌러야 OCR 시작

---

## 7. 접근 경로

- **로컬:** http://localhost:8080/cardconv
- **프로덕션:** http://134.209.62.57/cardconv
- **Google Drive:** `Wayfinder/Receipts/` (Drive 앱에서 직접 접근 가능)
- **접근 권한:** jongha.kang 계정 전용 (admin_only)
