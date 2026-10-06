# CaloDetect · 칼로디텍트

작업 전 [필수 적용 규칙](docs/rules/README.md)을 먼저 읽어 주세요.

- `docs/rules/`: 개발 규칙, 원본 업무지시서, 결정 대기 사항, 동의 초안
- `docs/design/`: 아키텍처와 데이터 스키마
- `docs/operations/`: 배포 및 기존 Streamlit 실행 안내 (프로젝트 루트에서 실행)
- `docs/planning/`: 구현 계획과 로드맵
- `docs/model/`: 모델 실험 및 현황
- `docs/UI_VALIDATION.md`, `docs/ui-preview/`: UI 검증과 화면 자료

루트에는 README·CHANGELOG·AGENTS 진입점과 실행·환경 설정·모델·데이터 파일을 둡니다.

식단 저장에 성공하면 “식단을 저장했습니다.” 안내와 함께 히스토리로 이동합니다. 저장한 음식명·섭취량·영양 정보를 확인할 수 있으며, 후속 정보 조회가 실패해도 방금 저장한 결과는 유지됩니다.

웹앱 새로고침 시 마지막 화면과 서버 로그인 세션을 복원합니다. 인증은 HttpOnly 쿠키로 유지하며 기본 만료는 24시간(`SESSION_HOURS`)입니다. 접속 주소는 동일하게 사용하세요. `localhost`와 `127.0.0.1`은 서로 다른 쿠키를 사용합니다.

홈페이지 상단에서도 로그인한 회원에게 “○○님 환영합니다”와 내 계정 버튼을 표시합니다.

회원 홈은 초록색 주간 달력과 식단 기록 카드로 구성합니다. 아침·점심·저녁·간식의 추가 버튼을 누르면 해당 식사 구분으로 기록 화면을 열며, 저장된 사진과 실제 영양 섭취량을 표시합니다. 모바일에서는 카드를 세로로 배치합니다.

PC의 모든 사용자 화면은 콘텐츠 영역 전체 너비를 사용하는 와이드 배치를 유지합니다. 홈 기록 안내의 문구·버튼과 식사 일러스트를 좌우로 배치합니다. 좁은 화면은 기존 반응형 배치를 사용합니다.

음식 추가의 영양 미리보기는 총 열량·탄단지 가로 누적 그래프·당류·나트륨을 표시합니다. 그래프는 실제 영양값을 4/4/9 kcal/g으로 환산한 구성 비율이며 목표 비율을 의미하지 않습니다.

히스토리는 음식 한 개당 한 행의 데이터베이스형 표로 날짜·식사·음식·섭취량과 6개 영양 수치를 표시합니다. 음식명 검색·식사 필터·날짜 정렬을 제공하며 모바일에서는 표를 가로로 스크롤할 수 있습니다.

홈의 주간 달력 날짜를 누르면 해당 날짜의 식단·저장 사진·영양 합계를 확인합니다. 날짜 입력으로 다른 주도 조회할 수 있고 “오늘로 돌아가기”로 오늘의 기록을 다시 표시합니다.

공통 로고는 `frontend/src/Visuals.jsx`의 Brand SVG와 워드마크로 표시하며 크기와 색상은 `frontend/src/reference.css`에서 조정합니다.

홈페이지 배너 배경은 `frontend/public/images/hero-bg.webp`를 사용합니다. 같은 파일명으로 교체하면 배경에 반영됩니다.

주요 기능 카드에는 같은 폴더의 `feature-meal.webp.png`, `feature-nutrition.webp.png`, `feature-recommendation.webp.png`, `feature-nearby.webp.png`를 사용합니다. 처음 세 카드는 기존 기능에 연결되며 주변 맛집·제품은 준비 중입니다.

음식 확인과 영양 계산을 기반으로 식단 기록·오늘 상태·식사 추천까지 연결하는 웹 서비스입니다. 내부 프로젝트 버전은 CaloDetect 2.0이며 사용자 화면에는 CaloDetect를 사용합니다.

**팀 공용 저장소 / Source of Truth:** <https://github.com/wndnsud-ui/CaloDetect>

UX 변경과 미확정 정책은 [보류 및 결정 대기 사항](docs/rules/PENDING_DECISIONS.md)에서 관리합니다. 목표 설정은 왼쪽 입력 카드와 오른쪽 칼로리 결과 카드로 구성합니다. 계산·저장 후에도 두 카드를 유지하며, 모바일에서는 결과가 입력 아래에 표시됩니다. 탄단지 비율은 확정 전까지 미설정으로 표시합니다.

개발 기준은 [v11 업무지시서](docs/rules/CaloDetect_Codex_통합_업무지시서_20261002_v11.md)입니다. 원문은 보존하며 결정 변경은 [CHANGELOG.md](CHANGELOG.md)에 기록합니다. 현재 회원·사진 분석·식단 저장·추천을 통합했습니다. **가입·이미지·추천 정책 설정은 팀 확정 전이며 운영 배포 상태가 아닙니다.**

## 현재 구현 범위

| 구성 | 현재 상태 |
|---|---|
| React + Vite 사용자 웹 | 첨부 이미지 기준 홈페이지, 로그인/가입, 회원정보 수정, 프로필·목표 저장, 사진 분석/수정, 식단 저장, 오늘 상태, History, 추천, 동의 설정 |
| FastAPI | 회원·프로필·식단·탐지·추천·Correction·관리자 QA API |
| PostgreSQL/SQLAlchemy | 회원/식단/탐지/추천/QA 영구 저장, 순차 Alembic revision 20261002_01 → 20261002_02 |
| 기존 YOLO26m | best.pt 재사용. 원본 유지. JPG/PNG 분석 API, 이미지별 탐지 ID 반환 |
| 기존 Streamlit | app.py 보존, 별도 streamlit/admin_qa.py 인증된 관리자 QA 클라이언트 추가 |
| 정책 미확정 | 동의 문구, 이미지 저장/보관, 추천 출처/기준·영양 목표 |

가상 회원/식단/추천 결과를 실제 데이터처럼 제공하지 않습니다. 영양값은 사용자 승인된 기존 `CaloDetect_nutrition_all_matched.csv`를 사용합니다. v11의 `(1).csv`는 현재 없으며 원본 데이터를 변경하지 않았습니다. 추천 엔진은 남은 칼로리·최근 음식 반복·제외 음식·선호 분류·다양성을 적용하고 실제 데이터의 영양값과 이유를 반환합니다. 미정 탄단지 목표·당류/나트륨 기준·끼니 적합성을 평가했다고 표시하지 않습니다.

## 새 웹 환경 실행

Node.js 22.12 이상(또는 20.19 이상), Python 3.12 권장. Windows PowerShell에서 아래 명령을 프로젝트 루트 기준으로 실행합니다. 기존 Streamlit 가상환경과 새 Backend 가상환경을 분리합니다.

```powershell
python -m venv .venv-backend
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-dev.txt
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_foods
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### 백엔드 실행 후 사용자 화면 열기

백엔드가 실행 중인 터미널은 그대로 두고, VS Code의 **터미널 → 새 터미널**에서 프런트엔드를 실행합니다. 아래 명령은 Windows PowerShell과 CMD에서 사용할 수 있습니다.

```powershell
cd C:\projects\CaloDetect\frontend
npm.cmd ci
npm.cmd run dev
```

`npm.cmd ci`는 처음 실행하거나 의존성이 변경됐을 때 실행합니다. 이미 설치했다면 `npm.cmd run dev`만 실행하면 됩니다.

터미널에 `Local: http://localhost:5173/`가 표시되면 브라우저에서 **<http://localhost:5173>**을 열어 홈페이지와 사용자 웹앱을 확인하세요. 백엔드 8000번 포트는 API용이고 React 화면은 5173번 포트에서 열립니다. 사용하는 동안 백엔드와 프런트엔드 터미널을 모두 켜 두고, 종료할 때 각 터미널에서 `Ctrl+C`를 누릅니다.

백엔드를 **8001번 포트**로 실행했다면 프런트엔드 실행 전에 같은 터미널에서 API 주소를 설정합니다. 이미 프런트엔드가 실행 중이면 `Ctrl+C`로 종료한 후 다시 실행하세요.

PowerShell:

```powershell
$env:CALODETECT_API_TARGET='http://127.0.0.1:8001'
npm.cmd run dev
```

CMD:

```cmd
set CALODETECT_API_TARGET=http://127.0.0.1:8001
npm.cmd run dev
```

웹: <http://localhost:5173> · API 문서: <http://127.0.0.1:8000/docs>. `npm.cmd`는 Windows PowerShell 실행 정책과 관계없이 npm을 호출합니다. macOS/Linux에서는 `npm` 및 `.venv-backend/bin/python`을 사용하세요. Vite 개발 서버가 `/api` 요청을 FastAPI에 전달합니다. 개발 포트는 5173을 사용하고 충돌 시 기존 프로세스를 확인하세요.

현재 음식·목표 미리 계산은 DB 없이 실행됩니다. 회원·프로필·식단·추천은 `.env`의 DATABASE_URL과 실행 중인 PostgreSQL, migration/seed가 필요합니다. 최초 시작 전 `.env.example`을 `.env`로 복사하고 값을 수정한 뒤 `docker compose up -d db`로 DB를 실행하세요. 기존 `.env`를 덮어쓰지 않습니다. `.env`, 비밀번호, API 키는 Git에 올리지 않습니다.

### 일간·월별 식단 분석

회원 홈의 오늘의 식단은 아침·점심·저녁·간식별 저장한 음식명·칼로리와 저장 완료 상태를 표시합니다. 사진 분석 결과를 식단으로 저장하면 해당 사진도 표시되며, 직접 입력한 식단은 직접 기록으로 표시합니다. 사진 선택만 한 상태는 저장된 식단에 포함되지 않습니다.

로그인 후 사이드바의 **식단 분석**에서 일간·월별 차트를 확인합니다. 날짜 또는 월과 영양 항목(칼로리·탄수화물·단백질·지방·당류·나트륨)을 선택할 수 있습니다. 일간 분석은 식사별 구성과 하루 합계를, 월별 분석은 일별 추이와 기록한 날의 하루 평균을 표시합니다. 월 차트의 날짜를 누르면 해당 일간 분석으로 이동합니다.

한국 시간의 식단 날짜를 기준으로 저장된 영양값을 Backend에서 집계합니다. 미기록일은 평균에서 제외하며 일부 식사만 기록한 날은 포함합니다. 영양소 목표·당류·나트륨 기준은 기존 미확정 상태를 유지합니다.

### 로컬 테스트 로그인

현재 개발 DB에 생성한 테스트 계정으로 로그인할 수 있습니다.

1. <http://localhost:5173>에 접속합니다.
2. 상단 **로그인**을 누르고 이메일 로그인 방식을 선택합니다.
3. 아래 이메일과 비밀번호를 입력합니다.

| 항목 | 값 |
|---|---|
| 이메일 | `test@calodetect.local` |
| 비밀번호 | `CaloTest!2026` |
| 권한 | 일반 사용자 (`user`) |

로컬 개발 전용 계정입니다. PostgreSQL과 Backend, Frontend가 실행 중이어야 하며, 다른 PC나 새 DB에는 자동으로 생성되지 않습니다. 새 DB에서는 아래 로컬 테스트 가입 설정을 적용한 후 화면에서 계정을 가입하세요.

### 정책 설정과 사진 분석 환경

사용자가 승인한 **로컬 이메일 테스트 가입**은 `.env`에 `APP_ENV=development`, `LOCAL_TEST_SIGNUP=true`, `FRONTEND_ORIGIN=http://localhost:5173`을 설정하고 Backend를 재시작하면 활성화됩니다. 만 18세 이상이며 화면의 테스트용 안내에 명시적으로 동의해야 합니다. 실제 개인정보 대신 테스트용 이름·이메일을 사용합니다. 승인된 `SERVICE_CONSENT_TEXT`가 없는 경우에만 테스트 안내를 사용하며 해당 내용을 개발 DB의 동의 이력에 저장합니다. 로컬 호스트와 루프백 접속에서만 허용하고 전달된 프록시 접속은 차단합니다. `APP_ENV=production` 또는 `LOCAL_TEST_SIGNUP=false`이면 테스트 가입을 허용하지 않습니다. `.env.example` 기본값은 운영 차단을 유지합니다. 소셜 가입은 이 테스트 설정으로 활성화하지 않습니다.

인증 방식은 이메일/비밀번호 및 사용자 요청으로 추가한 Google·Apple 로그인 + HttpOnly 세션 쿠키입니다. 로그인 후 마이페이지에서 이름을 수정할 수 있으며 이메일과 role 변경은 제공하지 않습니다. HTTPS 운영에서는 `COOKIE_SECURE=true`가 필요합니다. 홈페이지 기능 카드는 음식 영양 조회·목표 계산·오늘의 식단으로 연결되고 웹앱은 실제 API 기록을 표시합니다. 홈페이지의 휴대폰·포케·기능 카드·하단 배너 이미지 영역은 고품질 이미지 선정 전까지 빈 박스로 유지합니다. 회원 웹앱의 기존 CSS 식사 일러스트는 유지합니다. 위치 기반 맛집/포인트는 후속 범위입니다.

Vite의 `CALODETECT_API_TARGET` 환경변수로 검증용 API 주소를 바꿀 수 있습니다(기본 `http://127.0.0.1:8000`). 다른 웹 포트를 쓰면 Backend `FRONTEND_ORIGIN`도 해당 주소와 일치시켜야 합니다. 현재 compose.yaml은 정책 환경변수를 모두 전달하지 않으므로 컨테이너 실행에서는 로컬 compose override 또는 배포 환경변수를 사용하세요. 컨테이너 migration은 `docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head`로 실행합니다.

가입·로그인 최소 연령은 사용자 승인에 따라 **만 18세**이며 `AGE_MIN` 기본값은 `18`입니다. 가입 시 입력한 만 나이를 기준으로 검사하며 본인인증이나 생년월일에 따른 자동 갱신은 제공하지 않습니다. 기존 계정의 로그인과 인증 API도 연령을 확인합니다. `SERVICE_CONSENT_TEXT`는 아직 미확정이므로 승인된 문구가 설정되어야 회원가입을 활성화합니다. 동의 문구는 가입 요청과 DB에 보존합니다. 선택 모델 개선 동의는 `MODEL_IMPROVEMENT_CONSENT_TEXT` 확정·설정 후 활성화하며, 문구 미설정 상태에서도 기존 동의 철회는 허용합니다. `IMAGE_STORAGE_DIR` 미설정이면 사진 업로드는 정책 안내를 반환하고 음식 직접 선택·식단 저장은 가능합니다. `RECOMMENDATION_ENABLED=true`, `RECENT_MEAL_WINDOW`는 기존 CSV를 추천 출처로 사용하는 개발 기준이 승인된 뒤 설정합니다. 예시 `3`을 운영 정책으로 간주하지 않습니다. 연령 외 미확정 정책은 TBD를 유지합니다.

음식 추가 화면의 **사진 선택** 또는 **사진 바로 찍기**로 JPG/PNG(최대 10MB)를 선택하고 미리볼 수 있습니다. 모바일 촬영은 기기의 카메라 입력을 사용하고 PC는 웹캠 권한이 필요합니다(HTTPS 또는 localhost). 사진 선택은 로그인 없이 가능하며, 선택 사진은 로그인 중 유지되고 새로고침하면 해제됩니다. 로그인 후 **사진 분석하기 → 음식/섭취량 확인 → 식단 저장하기** 순서로 기록합니다. 촬영 취소·화면 이탈 시 웹캠 사용을 종료합니다. 서버 분석에는 기존 이미지 저장 정책 설정과 YOLO 환경이 필요합니다.

사진 분석은 기존 `.venv`가 있으면 그 Python/YOLO 환경을 재사용하는 worker를 호출합니다. 다른 PC에서 기존 환경이 없으면 새 환경에 설치합니다:

로컬 사진 분석 테스트는 `APP_ENV=development`, `LOCAL_TEST_IMAGE_ANALYSIS=true`, `IMAGE_STORAGE_DIR=.private-uploads`로 활성화합니다. Backend를 재시작한 뒤 로그인 → 사진 선택 → **사진 분석하기**를 누릅니다. 테스트 원본 사진은 Git에서 제외된 `.private-uploads`에 저장되고 분석 결과는 개발 DB에 기록됩니다. 자동 삭제·보관기간은 아직 정하지 않았으므로 테스트 사진만 사용하며, 이 설정을 운영 정책으로 사용하지 않습니다. 루프백 접속에서만 테스트 분석·원본 조회를 허용합니다. 모델 개선 선택 동의와 관리자 QA 조건은 유지합니다. YOLO 첫 실행 안내는 JSON 결과와 분리하고 런타임 설정은 `.runtime-logs/ultralytics`에 저장합니다.

```powershell
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-vision.txt
```

분석 기준은 conf=0.11, iou=0.45, imgsz=960, CPU입니다. 파일명 대신 서버 UUID로 이미지를 구분하고 사용자별 이미지 권한을 검사합니다. 탐지되지 않거나 추론 오류가 나도 직접 음식 선택을 제공합니다.

### Google·Apple 로그인 설정

로그인 화면 상단의 **로그인 / 회원가입**에서 방식을 선택합니다. 회원가입에는 **Google로 회원가입**, **Apple로 회원가입**, **이메일로 회원가입**을 제공하며, 소셜 가입은 비밀번호를 따로 입력하지 않습니다. 서버 설정이 없는 제공자는 연결 준비 상태를 안내하고 버튼을 누르면 진행할 수 없는 이유를 표시합니다. 기존 이메일 로그인은 신규 가입 동의 문구 설정 여부와 무관하게 사용할 수 있습니다. 새 소셜 계정은 제공자 인증 후 이름·만 나이·승인된 서비스 동의를 입력해 가입을 마칩니다. 기존 소셜 계정은 `(oauth_provider, oauth_subject)`로 로그인하며 이메일 변경으로 새 계정을 만들거나 기존 이메일 회원과 자동 연결하지 않습니다. Apple 이메일 가리기도 제공자가 확인한 이메일로 처리합니다. 기존 이메일과 충돌하면 기존 방식으로 로그인해야 하며 계정 연결 UI는 제공하지 않습니다.

사용자 요청에 따라 서비스 등록은 나중에 진행하고 [가입 동의 검토용 초안](docs/rules/SERVICE_CONSENT_DRAFT.md)을 작성했습니다. 초안을 환경변수로 자동 적용하지 않습니다. 현재 Google·Apple 등록 정보와 승인된 가입 동의 문구가 미설정이라 실제 소셜 인증·신규 가입은 활성화되지 않습니다.

1. Backend 의존성을 설치합니다: `.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements.txt`. 외부 ID 토큰은 PyJWT와 제공자 공개키로 서명·발급자·대상 앱·만료·nonce를 검증합니다. 5분짜리 서명된 HttpOnly 인증 요청 쿠키를 사용하며 Apple은 state도 확인합니다.
2. Google Cloud에서 웹용 OAuth 클라이언트를 만들고 실제 웹앱 주소를 승인된 JavaScript 원본으로 등록합니다. 개발용 원본 예: `http://localhost:5173`. `.env`에 `GOOGLE_CLIENT_ID`를 설정합니다. [Google Identity Services 설정](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid).
3. Apple Developer에서 Sign in with Apple을 활성화한 App ID에 웹용 Services ID를 연결하고 웹 도메인·HTTPS 반환 URL을 등록합니다. `.env`에 Services ID를 `APPLE_CLIENT_ID`, 등록한 반환 URL을 `APPLE_REDIRECT_URI`로 설정합니다. 실제 웹앱과 같은 원본의 HTTPS 주소를 사용합니다. Apple 웹 로그인은 localhost 개발 URL 대신 등록된 HTTPS 도메인에서 검증해야 합니다. [Apple 웹 설정](https://developer.apple.com/documentation/signinwithapple/configuring-your-webpage-for-sign-in-with-apple).
4. `.env`에 무작위 `OAUTH_STATE_SECRET`(32자 이상)을 설정합니다. 생성 예: `.\.venv-backend\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"`. 모든 Backend 인스턴스는 같은 값을 사용하며 저장소에 커밋하지 않습니다. HTTPS 환경에서는 `COOKIE_SECURE=true`, `FRONTEND_ORIGIN`은 실제 웹앱 원본으로 설정합니다.
5. 서버를 재시작하고 각 제공자의 로그인·취소·신규 가입·재로그인을 확인합니다. 기본 API와 `/api` 프록시를 같은 웹앱 원본에서 사용합니다. 소셜 로그인은 프로필 인증만 요청하며 Google Drive·Calendar 또는 Apple Health 권한을 요청하지 않습니다.

제공자 앱 자격정보가 없는 환경에서는 실제 Google/Apple 로그인 검증을 완료할 수 없습니다. 자동 테스트는 로컬 RSA 서명 토큰으로 인증 검증·18세 경계·동의·이메일 충돌을 검사하며 제공자 공개키 조회를 격리합니다. 기존 DB 식별자 컬럼과 비밀번호 NOT NULL 제약을 보존하여 migration은 추가하지 않습니다. 소셜 계정의 비밀번호 컬럼은 공개하지 않는 무작위 비밀번호 해시로 채우며 비밀번호 설정·계정 연결·소셜 토큰 갱신·제공자 연결 해제는 이번 범위에 포함하지 않습니다.

### 관리자 QA

최초 관리자는 A 담당이 내부 CLI로만 생성합니다. 공개 승격 API는 없습니다.

```powershell
.\.venv-backend\Scripts\python.exe -m backend.scripts.create_admin --email admin@example.com --age 승인된연령
.\.venv\Scripts\python.exe -m streamlit run streamlit/admin_qa.py --server.port 8502
```

비밀번호는 CLI에서 숨김 입력합니다. 관리자 QA는 FastAPI에 로그인하고 서버의 /admin/* API만 호출합니다. 일반 사용자는 403입니다. 동의한 사용자 수정만 PENDING 후보로 등록하고, 철회 시 대기 샘플을 제외합니다. APPROVED 이력은 유지하며 재수정은 새 검수 후보로 남깁니다. 실제 재학습은 구현하지 않았습니다.

## PostgreSQL / Docker 개발 실행

루트 `.env`에 개발용 `POSTGRES_PASSWORD`를 추가합니다. 예시 문자열을 실제 비밀번호로 쓰지 마세요. URL의 특수문자는 URL 인코딩이 필요합니다.

```powershell
docker compose up --build -d
```

이 구성은 PostgreSQL과 Backend만 실행합니다. Frontend는 위 npm 개발 명령으로 별도 실행합니다. `GET /health/database`로 DB 연결을 확인할 수 있습니다. `docker compose down`은 컨테이너를 중지하며 저장 volume은 유지합니다. 운영 배포 구성은 [DEPLOYMENT.md](docs/operations/DEPLOYMENT.md)를 참고하세요.

## 검사

확인 결과: 기존/회원/통합 테스트 22개 통과, 기본 검사에서 실제 YOLO smoke 1개 제외. 격리된 PostgreSQL에서 통합+실제 YOLO 업로드 7개 통과, migration/음식 적재 성공, React production build 및 pip check 성공. 브라우저 PC/모바일에서 가입→프로필 저장→이름 수정→새로고침→로그아웃/재로그인 후 저장값 복원 확인, JS 오류 및 가로 넘침 없음. 음식 정확도 성능 평가는 별도입니다. 테스트용 연령·동의·추천 설정은 운영 설정에 반영하지 않았습니다. [화면과 검증 상세](docs/UI_VALIDATION.md)를 참고하세요.

```powershell
.\.venv-backend\Scripts\python.exe -m pytest backend/tests -q
cd frontend
npm.cmd run build
```

실제 PostgreSQL+YOLO 검사(격리된 테스트 스키마 생성 후 제거):

```powershell
$env:RUN_POSTGRES_TESTS='1'
$env:RUN_VISION_TEST='1'
.\.venv-backend\Scripts\python.exe -m pytest backend/tests/test_p0_flow.py -q
Remove-Item Env:RUN_POSTGRES_TESTS
Remove-Item Env:RUN_VISION_TEST
```

기존 앱 검증은 기존 `.venv`에서 `python validate_data.py`로 수행합니다. 기존 데이터와 모델은 그대로 유지합니다.

## 팀 GitHub 협업 방침

모든 팀원은 이 저장소 하나를 기준으로 작업합니다. 외부 복사본이나 `.upload-repo`를 팀 기준으로 사용하지 않습니다. 로컬 작업 시작 전에 `git remote -v`로 origin이 `https://github.com/wndnsud-ui/CaloDetect.git`인지 확인하세요.

### 최초 클론

```bash
git clone https://github.com/wndnsud-ui/CaloDetect.git
cd CaloDetect
git remote -v
git switch main
git pull --ff-only origin main
```

기존 로컬 프로젝트가 이 저장소를 이미 연결했다면 다시 `git init`하거나 중첩 클론하지 않습니다. 필요한 경우 `git remote set-url origin https://github.com/wndnsud-ui/CaloDetect.git`으로 주소를 정정하세요.

### 브랜치와 작업 순서

`main`은 검증된 통합 코드입니다. 직접 대규모 변경·직접 push·force push를 하지 않습니다. `feature/*`, `fix/*`, `docs/*` 브랜치에서 작업하고 PR로 합칩니다. `develop`은 팀이 실제 생성하고 통합 기준으로 확정한 뒤 사용합니다. 현재 명령은 main 기준입니다.

```bash
git switch main
git pull --ff-only origin main
git switch -c feature/meal-scan
# 구현 → 테스트 → 변경 내용 확인
git status
git diff
git add 변경한파일경로
git commit -m "feat: 음식 분석 API 연결"
git push -u origin feature/meal-scan
```

`git add .` 대신 관련 파일을 지정하고 staged diff(`git diff --cached`)를 확인하세요. 새 기능/수정/문서는 `feat:`, `fix:`, `docs:` 등의 접두어로 기능 단위 커밋을 권장합니다. 개인 환경·비밀키·업로드 사용자 사진을 커밋하지 않습니다.

### PR와 머지

1. GitHub에서 작업 브랜치 → main으로 Pull Request를 만듭니다.
2. PR에 문제/변경 후 동작, 변경 범위, 실행한 검사와 결과, DB·의존성 변경, TBD 영향 여부를 적습니다.
3. 다른 팀원 최소 1명이 검토하고 테스트 결과를 확인한 후 합칩니다. 기능 단위 squash merge를 권장합니다.
4. 머지 후 로컬 main을 `git pull --ff-only origin main`으로 갱신합니다. 작업 브랜치는 필요 없어진 뒤 삭제합니다.

GitHub 관리자는 main에 PR 필수, 최소 승인 1명, force push/삭제 금지의 branch protection 또는 ruleset을 설정하는 것을 권장합니다. **이 README 작성만으로 GitHub 보호 설정이 적용되지는 않습니다.** CI 필수 검사 지정은 실제 CI가 추가된 뒤 설정합니다.

### 최신 main 반영과 충돌 해결

먼저 변경을 커밋하거나 `git stash push -m "작업 임시 보관"`으로 보관한 뒤 자신의 작업 브랜치에서:

```bash
git fetch origin
git merge origin/main
# 충돌이 있으면 파일의 충돌 표시를 해결하고 검사 실행
git add 해결한파일경로
git commit
git push
```

해결이 어려우면 담당자와 확인하고 `git merge --abort`로 병합 전 상태로 돌아갑니다. 공유 브랜치를 임의 rebase/force push하지 않습니다. `git reset --hard`, 원본 모델/CSV 덮어쓰기로 충돌을 해결하지 않습니다.

### 담당과 공동 파일

| 담당 | 범위 |
|---|---|
| A · Backend Core | Auth, Profile, DB, API schema, Meal/Today, 관리자 권한, Alembic |
| B · Vision/Data/Recommendation | YOLO, 기존 데이터, 추천, Detection/Correction, Streamlit QA |
| C · Frontend/Integration/Deploy | React, API 통합, Docker/배포 |

**Alembic revision 생성은 A만 수행합니다.** B/C는 필요한 스키마 변경을 A에게 전달합니다. 모델·CSV·YAML 원본은 보존합니다. 공동 파일 변경은 PR에서 명시하고, 요청·응답·오류 schema는 API 담당자와 맞춥니다. P1은 P0 완료 뒤에만 시작합니다.

### 매 작업 종료 확인

- 실제 변경 파일과 staged diff 확인, 관련 검사 실행.
- 실행법 변경 시 README, 정책 변경 시 CHANGELOG 갱신.
- 원본 업무지시서·모델·데이터 보존 및 secret 제외 확인.
- PR/머지 후 main 최신 상태 확인.

## 프로젝트 문서

[개발 규칙](AGENTS.md) · [구현 계획/TBD](docs/planning/IMPLEMENTATION_PLAN.md) · [구조](docs/design/ARCHITECTURE.md) · [데이터 스키마](docs/design/DATA_SCHEMA.md) · [모델 현황](docs/model/MODEL_EXPERIMENTS.md) · [로드맵](docs/planning/ROADMAP.md) · [변경 이력](CHANGELOG.md)

## 기존 Streamlit 실행 안내

최초 설치는 `01_SETUP_AND_RUN.bat`, 이후 실행은 `02_RUN_ONLY.bat`을 더블 클릭하세요.
현재 PC에 설치된 Python과 프로젝트 내 차트 패키지를 사용합니다.
가상환경이 있으면 해당 환경을 우선 사용하며, 준비된 환경이 없으면 설치 스크립트를 실행합니다.

## 모델 및 데이터

- `best.pt`: 프로젝트 폴더에 있는 최신 모델 (150 클래스)
- `data.yaml`: 클래스 번호 0~149와 한글 음식명
- `CaloDetect_nutrition_all_matched.csv`: YAML 순서대로 정렬된 150행
- `data_config.py`: 경로와 컬럼 정의, 데이터 검증
- `validate_data.py`: 실제 모델/YAML/CSV 매칭 확인

앱은 프로젝트 폴더의 `best.pt`를 사용합니다. 모델을 교체한 뒤에는 실행 중인 앱을 종료하고 다시 실행하세요.
앱, YAML, CSV, 샘플 경로는 실행하는 폴더에 영향을 받지 않습니다.

## 영양 CSV 컬럼

| 컬럼 | 의미 / 단위 |
| --- | --- |
| class_id | data.yaml의 클래스 번호 (0~149) |
| food_name | 모델의 한글 음식명과 정확히 일치 |
| category | 음식 분류 |
| unit | 영양값의 기준 섭취량 (원본 값 유지) |
| cal | kcal |
| carbs | 탄수화물 g |
| protein | 단백질 g |
| fat | 지방 g |
| sugar | 당류 g |
| sodium | 나트륨 mg |

영양 수치는 원본 그대로 유지했습니다. 각 수치는 `unit`에 적힌 기준량의 값입니다.
음식명 누락/중복, 잘못된 클래스 번호, 빈 분류/기준량, 음수 또는 잘못된 영양 수치는 실행 시 오류로 알려줍니다.

## 다른 PC에서 최초 설치

Python 3.10 이상이 설치된 상태에서 `01_SETUP_AND_RUN.bat`을 실행하세요.
패키지 설치 후 모델과 컬럼을 검증하고 Streamlit을 실행합니다.
이후에는 `02_RUN_ONLY.bat`을 실행하세요.

직접 실행하는 경우 이 폴더에서:

```powershell
python -m pip install -r requirements.txt
python validate_data.py
python -m streamlit run app.py
```

접속 주소: http://localhost:8501

샘플 사진은 `samples/` 폴더에 넣거나 화면에서 업로드할 수 있습니다.
