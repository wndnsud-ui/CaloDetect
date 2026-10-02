# CaloDetect · 칼로디텍트

음식 확인과 영양 계산을 기반으로 식단 기록·오늘 상태·식사 추천까지 연결하는 웹 서비스입니다. 내부 프로젝트 버전은 CaloDetect 2.0이며 사용자 화면에는 CaloDetect를 사용합니다.

**팀 공용 저장소 / Source of Truth:** <https://github.com/wndnsud-ui/CaloDetect>

개발 기준은 [v11 업무지시서](CaloDetect_Codex_통합_업무지시서_20261002_v11.md)입니다. 원문은 보존하며 결정 변경은 [CHANGELOG.md](CHANGELOG.md)에 기록합니다. 현재 회원·사진 분석·식단 저장·추천을 통합했습니다. **가입·이미지·추천 정책 설정은 팀 확정 전이며 운영 배포 상태가 아닙니다.**

## 현재 구현 범위

| 구성 | 현재 상태 |
|---|---|
| React + Vite 사용자 웹 | 첨부 이미지 기준 홈페이지, 로그인/가입, 회원정보 수정, 프로필·목표 저장, 사진 분석/수정, 식단 저장, 오늘 상태, History, 추천, 동의 설정 |
| FastAPI | 회원·프로필·식단·탐지·추천·Correction·관리자 QA API |
| PostgreSQL/SQLAlchemy | 회원/식단/탐지/추천/QA 영구 저장, 순차 Alembic revision 20261002_01 → 20261002_02 |
| 기존 YOLO26m | best.pt 재사용. 원본 유지. JPG/PNG 분석 API, 이미지별 탐지 ID 반환 |
| 기존 Streamlit | app.py 보존, 별도 streamlit/admin_qa.py 인증된 관리자 QA 클라이언트 추가 |
| 정책 미확정 | 가입 연령·동의 문구, 이미지 저장/보관, 추천 출처/기준·영양 목표 |

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

다른 터미널에서:

```powershell
cd frontend
npm.cmd ci
npm.cmd run dev
```

웹: <http://localhost:5173> · API 문서: <http://127.0.0.1:8000/docs>. `npm.cmd`는 Windows PowerShell 실행 정책과 관계없이 npm을 호출합니다. macOS/Linux에서는 `npm` 및 `.venv-backend/bin/python`을 사용하세요. Vite 개발 서버가 `/api` 요청을 FastAPI에 전달합니다. 개발 포트는 5173을 사용하고 충돌 시 기존 프로세스를 확인하세요.

현재 음식·목표 미리 계산은 DB 없이 실행됩니다. 회원·프로필·식단·추천은 `.env`의 DATABASE_URL과 실행 중인 PostgreSQL, migration/seed가 필요합니다. 최초 시작 전 `.env.example`을 `.env`로 복사하고 값을 수정한 뒤 `docker compose up -d db`로 DB를 실행하세요. 기존 `.env`를 덮어쓰지 않습니다. `.env`, 비밀번호, API 키는 Git에 올리지 않습니다.

### 정책 설정과 사진 분석 환경

인증 방식은 사용자 승인된 이메일/비밀번호 + HttpOnly 세션 쿠키입니다. 로그인 후 마이페이지에서 이름을 수정할 수 있으며 이메일과 role 변경은 제공하지 않습니다. HTTPS 운영에서는 `COOKIE_SECURE=true`가 필요합니다. 홈페이지 휴대폰 모형의 수치는 화면 예시이고 웹앱은 실제 API 기록을 표시합니다. 첨부 디자인의 음식 사진 대신 로컬 CSS 식사 일러스트를 사용합니다. 위치 기반 맛집/소셜 로그인/포인트는 후속 범위입니다.

Vite의 `CALODETECT_API_TARGET` 환경변수로 검증용 API 주소를 바꿀 수 있습니다(기본 `http://127.0.0.1:8000`). 다른 웹 포트를 쓰면 Backend `FRONTEND_ORIGIN`도 해당 주소와 일치시켜야 합니다. 현재 compose.yaml은 정책 환경변수를 모두 전달하지 않으므로 컨테이너 실행에서는 로컬 compose override 또는 배포 환경변수를 사용하세요. 컨테이너 migration은 `docker compose exec backend python -m alembic -c backend/alembic.ini upgrade head`로 실행합니다.

가입은 `AGE_MIN`과 `SERVICE_CONSENT_TEXT`가 팀에서 확정되어 설정된 경우에만 활성화합니다. 동의 문구는 가입 요청과 DB에 보존합니다. 선택 모델 개선 동의는 `MODEL_IMPROVEMENT_CONSENT_TEXT` 확정·설정 후 활성화하며, 문구 미설정 상태에서도 기존 동의 철회는 허용합니다. `IMAGE_STORAGE_DIR` 미설정이면 사진 업로드는 정책 안내를 반환하고 음식 직접 선택·식단 저장은 가능합니다. `RECOMMENDATION_ENABLED=true`, `RECENT_MEAL_WINDOW`는 기존 CSV를 추천 출처로 사용하는 개발 기준이 승인된 뒤 설정합니다. 예시 `3`을 운영 정책으로 간주하지 않습니다. 모든 정책은 현재 TBD이며 자동 활성화하지 않았습니다.

사진 분석은 기존 `.venv`가 있으면 그 Python/YOLO 환경을 재사용하는 worker를 호출합니다. 다른 PC에서 기존 환경이 없으면 새 환경에 설치합니다:

```powershell
.\.venv-backend\Scripts\python.exe -m pip install -r backend/requirements-vision.txt
```

분석 기준은 conf=0.11, iou=0.45, imgsz=960, CPU입니다. 파일명 대신 서버 UUID로 이미지를 구분하고 사용자별 이미지 권한을 검사합니다. 탐지되지 않거나 추론 오류가 나도 직접 음식 선택을 제공합니다.

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

이 구성은 PostgreSQL과 Backend만 실행합니다. Frontend는 위 npm 개발 명령으로 별도 실행합니다. `GET /health/database`로 DB 연결을 확인할 수 있습니다. `docker compose down`은 컨테이너를 중지하며 저장 volume은 유지합니다. 운영 배포 구성은 [DEPLOYMENT.md](DEPLOYMENT.md)를 참고하세요.

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

[개발 규칙](AGENTS.md) · [구현 계획/TBD](IMPLEMENTATION_PLAN.md) · [구조](ARCHITECTURE.md) · [데이터 스키마](DATA_SCHEMA.md) · [모델 현황](MODEL_EXPERIMENTS.md) · [로드맵](ROADMAP.md) · [변경 이력](CHANGELOG.md)

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
