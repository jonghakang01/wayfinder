# 출장 내역 SAP 상신 자동화
- 상태: approved (2026-08-03 강프로 — Q2 건마다 확인 후 제출, Q3 출장 건은 비출장 엑셀에서 제외)
- 대상: cardconv (출장 구분·내보내기) + 로컬 자동화 스크립트 (Windows Edge)

## 문제
비출장 경비는 Review의 SAP 엑셀로 일괄 업로드가 되지만, 출장 경비는 SAP의
출장 상신 화면에 **한 건씩 수기 입력**해야 한다. 입력 항목은 매번 같은데
일괄 업로드 기능이 SAP에 없다 (강프로, 2026-08-03).

## 목표
- cardconv에서 출장 건을 표시(항목명/출장명 기입)하면,
- 로컬 스크립트가 강프로의 **실제 Edge 창**(회사 SSO 세션 그대로)을 조종해
  출장 건을 한 건씩 SAP 상신 화면에 자동 기입한다.
- 각 건의 최종 제출 직전에 멈춰 사람이 확인 후 넘어간다(기본값 — 미결 Q2).

## 비목표 (이번엔 안 한다)
- SAP 비밀번호/SSO 자동 로그인 — 로그인은 사람이 이미 되어 있는 Edge를 쓴다.
- 첨부파일(영수증 이미지) 자동 업로드 — 1차는 필드 기입까지, 첨부는 관찰 후 별건.
- 비출장 경비 흐름 변경 — 기존 엑셀 일괄 업로드 그대로.
- prod 서버에서 실행 — 회사망 SAP은 강프로 PC에서만 접근 가능. 스크립트는 로컬 전용.

## 사용자 흐름
1. cardconv Review에서 출장 건들에 출장명(항목명) 기입 → 출장 묶음으로 구분됨
2. "Trip submission" 내보내기 → 상신용 데이터(JSON) 생성
3. Windows에서 Edge를 원격조종 모드로 실행(바로가기 1클릭, 최초 1회 설정)
4. 스크립트 실행 → SAP 상신 화면으로 이동해 1건 기입 → 확인 대기 → 제출 → 다음 건
5. 끝나면 건수·성공/실패 요약 출력

## 기술 구조
- Edge를 `--remote-debugging-port`로 기동(CDP) → WSL의 Playwright가 접속해
  **강프로의 실세션 Edge**를 조종. 별도 RPA 제품·로그인 저장 불필요.
- 선례: Windows 브릿지(powershell)·Teams notebot(브라우저 무인조작) 패턴 재사용.
- 화면이 바뀌면 셀렉터만 수선하면 됨 — 셀렉터는 설정 파일로 분리.

## 데이터
- cardconv 엔트리 신규 키: `trip_name` (str|None, 기본 None). None=비출장(기존과 동일).
- 마이그레이션: 없음(신규 키, 기존 데이터는 None으로 읽힘). 롤백 무해.
- 상신용 내보내기: `~/.appdata/cardconv/out/trip_submit_<날짜>.json`
  (한 건 = SAP 화면 필드명→값 매핑. 필드 목록은 Phase A에서 확정)

## 영향 표면
- cardconv Review/Ledger: 출장명 기입 UI(인라인 편집 or 벌크 지정) — cardconv
  기존 패턴(인라인 편집, 벌크액션 바) 재사용
- 기존 SAP 엑셀 내보내기: **출장 건 제외** 여부 확인 필요(미결 Q3)
- 모바일/테마: 기입 UI가 기존 표 안이라 기존 규약 따름
- 권한: 강프로 계정 데이터에만 해당(멀티테넌트 영향 없음)

## 진행 단계
- **Phase A (탐사·30분)**: Edge 디버그 모드로 SAP 상신 화면을 강프로가 한 번
  열어주면, 쭌이 화면 구조(필드·버튼)를 읽어 매핑 확정 → 스펙에 필드표 추가
- **Phase B**: cardconv에 trip_name 기입 UI + trip JSON 내보내기 (+테스트)
- **Phase C**: 자동 기입 스크립트 + 1건 실입력 리허설(제출 직전 멈춤) → 검수 후 실전

## 수용 조건
- [ ] 출장명이 기입된 건만 상신 대상에 들어간다
- [ ] 스크립트가 N건을 순서대로 기입하고, 각 건 제출 전 확인을 기다린다
- [ ] 실패한 건은 건너뛰고 마지막에 목록으로 보고한다(중간에 죽지 않음)
- [ ] SAP 화면 요소를 못 찾으면 그 자리에서 멈추고 어떤 요소인지 알려준다
- [ ] cardconv 기존 엑셀 내보내기/매칭 동작 불변 (pytest + smoke 통과)

## Phase A 결과 — 필드 매핑 (2026-08-03 실화면 실측)
화면 = `gate3.cheil.com/gte/exp_2010_p05.do` "Business Trip Settlement Other Expense".
URL이 이미 출장(Biz Trip No)에 스코프됨 — 사용자가 해당 출장 화면을 연 상태에서 로봇 시작.
한 건 입력 → Save → 그리드에 쌓임(Total N) → New → 다음 건.

| 화면 항목 | 요소 id | cardconv 값 |
|---|---|---|
| Receipt Type* | `rctScCd` | receipt_type: A→Cash, D→Corporate Credit Card |
| Inv. Date* | `docDt` | date (MM-DD-YYYY로 변환) |
| Purpose* | `exCntnt` | purpose (+companions) |
| Reason for Cash | `cashRsn` | cash_reason (cash 건만) |
| Account/Item* | `acttCd` (+`rctActtList` 최근목록) | gl |
| Amount* | `totDocAmt` | amount |
| Vendor Name* | `hbrdCdu`(Domestic/Overseas) + `upNm` | merchant (해외출장이면 Overseas) |
| Currency*/환율 | `crncyCd`/`aplcExrt` | USD/1.0 (기본값 그대로) |
| Payee·Posting Date·Tax Code·Cost Center·Biz Trip No | prefilled | 건드리지 않음 |
| 저장 | `btnSave` → `btnNew` | 건마다 확인 후 |

리허설에서 확정할 것: docDt 달력 위젯 입력 방식, acttCd 직접 입력 시 이름 자동조회
여부, Save 시 confirm/alert 처리.

## 리스크 / 미결 질문
- R. SAP 화면 구조에 전적으로 의존 — 화면 개편 시 셀렉터 수선 필요(설정 분리로 완화).
- ~~Q1~~ Phase A로 해소. ~~Q2~~ 1회차 화면 검증 후 **전자동(Save 포함)으로 변경**(강프로
  2026-08-03 "save까지 알아서") — 매 건 그리드 Total 증가로 저장 검증, `--confirm`으로
  건별 확인 모드 복귀 가능. Q3=엑셀에서 제외(승인, Phase B 반영).
- 추가(2026-08-03): Review 툴바 🤖 Robot 버튼(admin 전용) = `wayfinder-robot://` 프로토콜
  → sap-robot-edge.bat(중계기 자동기동+포털 2탭). 1회 등록 = install-robot-protocol.bat.
- 추가(2026-08-03 밤, 원버튼화): 🤖 버튼이 **로봇 콘솔까지 기동** — bat이
  run-trip-robot.sh(WSL 창)를 함께 띄우고, 로봇은 인자 없이 시작하면 ①Downloads의
  최신 trip_submit_*.json 자동 선택(24h 초과 시 확인 질문) ②출장 1개면 자동/여럿이면
  번호 선택 ③Other Expense 화면이 열릴 때까지 최대 15분 폴링 대기 후 자동 기입.
  flock으로 이중 실행 방지. 수동 실행(파일·출장명 인자)도 그대로 동작.
  → 남은 수동 = 태그 기입·✈ export 클릭·🤖 클릭·SAP 화면 진입뿐(터미널 단계 소멸).
