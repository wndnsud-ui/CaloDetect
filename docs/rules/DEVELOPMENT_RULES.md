# CaloDetect 개발 규칙

기준: 2026-10-20, 구현 커밋 `ed87d68`. 상세 기능과 근거는 [현재 구현 기준](CURRENT_IMPLEMENTATION.md)을 따른다.

- 사용자의 명시적 결정이 우선한다. 후속 결정은 CHANGELOG.md에 기록한다. 문서 정리가 새로운 기능·정책 승인을 의미하지 않는다.
- Master Spec `CaloDetect_Codex_통합_업무지시서_20261002_v11.md` 원문은 수정하지 않는다. 원문의 P0/P1 구분은 후속 승인된 챗 식사기록·커뮤니티·리워드 범위를 되돌리는 근거로 사용하지 않는다.
- 기존 프로젝트 전체 재작성, 관련 없는 대규모 수정, 모델·CSV·YAML 원본 덮어쓰기 금지. 기존 class_id/food_name 연결을 유지한다.
- 사용자 웹·관리자는 React, Backend는 FastAPI/SQLAlchemy/Pydantic/PostgreSQL. Streamlit은 `streamlit/charts.py` 그래프 서버만 유지한다. 폐기된 독립 app.py·Streamlit 관리자 QA를 복구하지 않는다.
- 사진 모델 개선·재학습은 폐기했다. 동의·학습 후보 수집·재학습 QA API/화면/DB 구조를 다시 추가하지 않는다. 음식명 수정은 탐지 기록에만 반영한다. 기존 음식 인식 모델은 유지한다.
- 영양·보상·추천 수치는 Python/DB가 계산한다. LLM이 수치를 생성하거나 계산하지 않는다. 현재 별도 LLM 서비스는 없다.
- 현재 범위는 회원·프로필·사진 인식·식단·분석·추천·챗 기록·커뮤니티·리워드 Stage A/B/C다. 기능 플래그와 권한 제한을 유지한다. 전문 코칭은 신청·차감 없는 화면 시안이다.
- 리워드는 lot/spend/allocation 원장·중복 지급 방지·계정 잠금 순서를 유지한다. 보상 실패가 식단 저장을 막지 않도록 격리한다. 온보딩·커뮤니티 출처의 실물 교환 제한을 유지한다.
- 관리자 API는 서버에서 admin 권한을 검사한다. 일반 사용자 역할 변경 API 금지. 테스트 메뉴·더미 생성은 로컬 개발 테스트 계정 본인만 허용한다.
- Alembic migration은 Backend Core A 담당 범위에서 작성한다. 이미 승인·구현한 리워드 및 폐기 migration은 보존한다. 새로운 파괴적 DB 작업은 별도 범위를 확인한다.
- 개발 기본값과 운영 확정값을 구분한다. TBD를 임의 확정하지 않는다. 개인 .env·DB·사진·로그·비밀키를 Git에 올리지 않는다.
- 변경 후 관련 검사를 수행한다. 실행법 변경은 루트 README, 결정은 CHANGELOG, 미결 사항은 PENDING_DECISIONS에 반영한다. 과거 검증 기록을 새 검증 결과로 간주하지 않는다.
- 팀 원격은 `https://github.com/wndnsud-ui/CaloDetect.git`. 기본은 작업 브랜치·PR 절차다. 사용자 승인(2026-10-20)으로 `ed87d68`을 develop에 반영했으며 main은 변경하지 않았다. 이 승인을 향후 모든 직접 push의 상시 승인으로 확대하지 않는다. force push 금지.
