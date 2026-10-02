# 개발 실행과 배포 준비

현재 Docker 구성은 로컬 개발용 Backend/PostgreSQL이다. 운영 배포 완료로 간주하지 않는다. React build 산출물은 frontend/dist이며 운영에서는 정적 호스팅 또는 reverse proxy가 /api를 FastAPI로 전달해야 한다. Vite proxy는 개발 서버에서만 적용된다.

운영 배포 전: 인증 방식·가입 연령·이미지 보관/저장·동의·추천 출처 확정, PostgreSQL migration(A), HTTPS/접근 제어, secret 관리, CORS 실제 origin, DB 백업, 업로드 용량/권한/삭제 정책, Auth rate limit, 사용자 분리·QA 권한·재로그인 유지·KST 경계 검증 필요.

현재는 인증과 개인정보 저장을 제공하지 않는다. /profiles/calorie-preview는 입력값을 저장하지 않는다. /health/database는 상세 예외나 접속 정보를 노출하지 않는다.

참고 구현 문서: [FastAPI](https://fastapi.tiangolo.com/tutorial/), [Vite](https://vite.dev/guide/), [SQLAlchemy](https://docs.sqlalchemy.org/en/20/orm/quickstart.html).
