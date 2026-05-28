# webapp — Project CLAUDE.md

## 프로젝트 개요
Python HTTPServer 기반 웹앱. 서비스 모듈 방식으로 기능 분리.

- **서버**: `server.py` (포트 8080)
- **서비스 디렉토리**: `services/` — auth, todo, chat, habits, aeo, dashboard 등
- **프로덕션**: `134.209.62.57`

## 팀 역할
| 작업 유형 | 담당 |
|-----------|------|
| 신규 서비스 모듈 추가 | 민준(설계) → 지훈(구현) |
| 버그 수정 | 지훈(개발) |
| 배포 전 검증 | 태양(QA) — smoke-test 필수 |

## 배포 규칙
- `git push` 전 반드시 smoke-test 통과:
  ```bash
  bash scripts/smoke-test.sh http://localhost:8080
  ```
- FAIL 항목 있으면 배포 차단

## 서비스 추가 시 체크리스트
1. `services/<name>.py` 생성
2. `services/__init__.py`에 import 추가
3. `smoke-test.sh`에 엔드포인트 검증 항목 추가
4. 태양에게 QA 요청

## 환경변수
`.env` 파일로 관리 (git 제외). `server.py`에서 자동 로드.
