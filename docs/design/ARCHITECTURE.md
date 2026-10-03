# 아키텍처

React 사용자 웹 → FastAPI API/서비스 → SQLAlchemy → PostgreSQL.
FastAPI Vision 서비스는 원본 best.pt와 data.yaml을 사용한다. 영양 서비스는 기존 CSV의 class_id/food_name 연결을 유지한다.
기존 Streamlit app.py는 보존된다. 관리자 QA 화면은 추후 인증된 FastAPI /admin/* 호출 방식으로 추가하며 DB 직접 쓰기를 허용하지 않는다.

현재 구현: 회원/HttpOnly 세션·CSRF, 프로필/목표 저장, 사진 YOLO 분석, 영양 배율 계산, 식단 영구화, KST 오늘 상태/History, 독립 추천 서비스, Correction/동의 철회, 관리자 QA API와 Streamlit 클라이언트.
회원 API는 기존 accounts.py를 통합하며 Meal API는 api.py에 분리한다. 사진은 사용자 권한 확인 후 전용 endpoint로 조회하고 정적 공개 폴더에 노출하지 않는다. Vision worker는 기존 .venv 모델 환경을 재사용한다.
추천은 실제 CSV 수치만 사용하며 미정 영양 목표를 생성하지 않는다. 가입·사진·추천 활성화 정책은 .env에 팀 승인값을 설정해야 한다. 기본값으로 임의 활성화하지 않는다.
UTC timestamp / Asia/Seoul 사용자 날짜. 브라우저에 secret/DB 연결 문자열을 전달하지 않는다.
