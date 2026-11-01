# 개발 실행과 배포 준비

현재 배포 구성은 React 프런트(Vercel), FastAPI API(Railway `CaloDetect` production), 그래프(Railway `calodetect-charts`), 공유 PostgreSQL/비공개 이미지 저장(Supabase)이다. 운영 정책 최종 확정과 실제 배포 상태는 구분한다. 프런트 `/api` 프록시는 `frontend/vercel.json`을 사용하며 Vite proxy는 로컬 개발 전용이다.

운영 배포 전: 인증 방식·가입 연령·이미지 보관/저장·동의·추천 출처 확정, PostgreSQL migration(A), HTTPS/접근 제어, secret 관리, CORS 실제 origin, DB 백업, 업로드 용량/권한/삭제 정책, Auth rate limit, 사용자 분리·QA 권한·재로그인 유지·KST 경계 검증 필요.

회원 인증과 사용자별 식단/프로필을 제공한다. `/profiles/calorie-preview`는 계산만 수행하고 `/health/database`는 접속 정보·내부 예외를 노출하지 않는다.

## 2026-11-01 직접 등록 개선 배포 기준

- API 소스: `wndnsud-ui/CaloDetect`의 `main`, 프로젝트 루트 기준 `backend/Dockerfile`. 서비스 도메인의 대상 포트는 8000이며 기존 시작 모듈은 `python -m backend.scripts.start`이다.
- API 주소: `https://calodetect-production.up.railway.app`. 프런트: `https://calo-detect.vercel.app`. 이 주소들은 공개 서비스 주소이며 비밀값은 문서에 기록하지 않는다.
- Railway `DATABASE_URL` 및 이미지 Storage는 승인된 공유 Supabase와 같은 대상으로 확인했다. `RUN_MIGRATIONS_ON_START=false`를 유지한다. 이번 schema/식약처 적재는 이미 담당 작업으로 적용했으므로 컨테이너 시작에서 다시 실행하지 않는다.
- 추가 명시 설정: `DB_POOL_MODE=session`(Session pooler 5432), `MEAL_LOW_CONFIDENCE_THRESHOLD=0.5`(조정 가능한 개발 기본값). 새 API 키는 필요 없다. 음식 사진은 YOLO로만 분석하며 별도 LLM 영양 추정 endpoint는 없다.
- DB 필요 revision: `20261101_01`. `nutrition_foods` 19,617건 및 RLS, 기존 모델 `foods` 150건을 확인했다. 스키마·원본 검증·백업 기록은 [직접 등록 개선 기록](../planning/MEAL_FALLBACK_IMPLEMENTATION.md)에 있다.
- XLSX 적재용 `openpyxl`은 `backend/requirements-dev.txt`에 있다. 이미 적재된 카탈로그 조회에는 필요하지 않으므로 Railway 런타임에 별도 등록할 의존성은 없다.
- 챗봇 식사 종류·음식 변경은 기존 모델/원장을 사용하며 추가 migration이 필요 없다. 기존 Coach의 문장 해석 설정을 재사용한다.
- 배포 전 검사: Backend 349통과·10제외(외부 DB/모델 opt-in 검사 제외), React production build, PC/모바일 격리 브라우저 검사. 공개 API 배포 후에는 health·DB health 및 OpenAPI의 검색/미리보기/PATCH 경로를 확인한다. 실제 회원 식단을 배포 검사 목적으로 생성/수정하지 않는다.

참고 구현 문서: [FastAPI](https://fastapi.tiangolo.com/tutorial/), [Vite](https://vite.dev/guide/), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/quickstart.html).
