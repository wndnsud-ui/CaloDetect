# CaloDetect 개발 규칙

- Master Spec: `docs/rules/CaloDetect_Codex_통합_업무지시서_20261002_v11.md`. 원문은 수정하지 않는다.
- 기존 프로젝트 전체 재작성, 기존 동작 코드 삭제, 모델/CSV/YAML 덮어쓰기 금지.
- 사용자 웹은 React, Backend는 FastAPI/SQLAlchemy/Pydantic/PostgreSQL. 기존 Streamlit 보존.
- P0 우선. P1/Backlog의 빈 API나 파일을 미리 생성하지 않는다.
- TBD를 임의 확정하지 않는다. 결정은 CHANGELOG.md에 기록한다.
- Python/DB가 계산하고 LLM은 설명만 한다. P0에 LLM 없음.
- Correction은 동의 확인과 관리자 QA 후에만 학습 후보로 사용한다.
- 일반 사용자 role 변경 금지. 관리자 QA는 Backend API를 사용한다.
- Alembic migration은 Backend Core A 담당 범위에서만 생성한다.
- 변경 후 테스트, README와 실제 실행법 일치, 관련 없는 파일 대규모 수정 금지.
- 기존 CSV 사용은 2026-10-02 사용자 승인됨. 기존 class_id/food_name 연결 유지.
- 팀 Source of Truth는 https://github.com/wndnsud-ui/CaloDetect.git. README의 clone/feature branch/PR/merge 절차를 따른다. main 직접 대규모 변경 및 force push 금지.
