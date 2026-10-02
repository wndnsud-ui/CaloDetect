# UI / 회원 기능 검증 — 2026-10-02

첨부 CaloDetect 인포그래픽을 기준으로 홈페이지, 브랜드 색상, 모바일 모형, 기능 카드, 회원 화면, 대시보드, 회원정보 수정 화면을 구현했다. 음식 이미지 대신 로컬 CSS 일러스트를 사용한다. 마케팅 휴대폰 모형 수치는 화면 예시로 표시하고 실제 웹앱은 API 기록만 표시한다. 지도/주변 맛집, 소셜 로그인, 포인트는 후속 범위로 남겼다.

## 화면

- [홈페이지 PC](ui-preview/landing-desktop.png)
- [대시보드 PC](ui-preview/dashboard-desktop.png)
- [홈페이지 모바일](ui-preview/landing-mobile.png)
- [회원정보 모바일](ui-preview/profile-mobile.png)

화면의 계정·동의 문구는 격리된 검증 DB에만 존재하는 테스트 자료다. 실제 서비스 연령/동의 정책으로 사용하지 않는다.

## 검증 결과

- Backend: `python -m pytest backend/tests -q` → 22 passed, 1 skipped. 기본 검사에서는 실제 YOLO smoke를 제외하며 별도 검사에서 실행했다.
- PostgreSQL: 기존 DB와 분리한 임시 PostgreSQL 16 컨테이너에서 Alembic 단일 체인 적용 확인. `RUN_POSTGRES_TESTS=1`, `RUN_VISION_TEST=1`의 P0 통합 검사 → 7 passed. YOLO 검사는 빈 이미지의 정상 업로드/탐지 경로와 수동 선택 fallback을 확인하며 실제 음식 정확도 평가가 아니다.
- 브라우저: Microsoft Edge / Playwright, PC 1440px 및 모바일 390px. 음식 영양 계산 → 목표 미리 계산 → 가입 → 프로필 저장 → 이름 수정 → 새로고침 후 세션 유지 → 로그아웃 → 재로그인 후 이름/프로필 복원 확인. JavaScript 오류 없음. 모바일 가로 넘침 수정 및 재검증 완료.
- React production build 성공, Backend pip check 성공. 원본 app.py, 모델, CSV, data.yaml 및 Master Spec은 보존.

## 설정과 제한

이메일/비밀번호 + HttpOnly 세션 쿠키 방식은 사용자가 승인했다. AGE_MIN, SERVICE_CONSENT_TEXT는 추후 전달 예정으로 미설정 환경에서 가입을 차단한다. 모델 개선 선택 동의는 MODEL_IMPROVEMENT_CONSENT_TEXT 확정 후 활성화하며 기존 동의 철회는 가능하다. 이미지 보관/추천 정책 역시 자동 확정하지 않는다.

일반 사용자 로그인 응답에는 원문 세션 토큰을 반환하지 않는다. 세션 저장은 해시, 변경 요청은 CSRF 검사, 이름 외 회원정보/role 변경 입력은 거부한다. 관리자 Streamlit QA 내부 로그인은 별도 API 인증 토큰을 사용하며 사용자 웹에 관리자 토큰을 반환하지 않는다.

작업은 `feature/reference-ui-profile`의 로컬 변경으로 제공한다. 기존 작업 파일을 보존했고 main merge/push는 하지 않았다. 실행법은 루트 README를 따른다.
