# 인식 실패 대체 기록 구현 및 적용

2026-11-01 · 작업 브랜치 `feature/chatbot`. Master Spec 원문은 변경하지 않았다.

**최신 사용자 결정:** 음식 사진은 YOLO만 분석한다. LLM 영양 추정 버튼·API·전용 서비스를 제거했다. 아래의 LLM 관련 구현/테스트 기록은 이전 단계의 기록이며 현재 제공 기능이 아니다. 기본 흐름은 사진 선택 → 「사진 분석하기」 → YOLO → 실패 시 DB 검색/직접 입력이다. 현재 검증: 관련 Backend 67통과·1제외, PC 1440px/모바일 390px에서 음식 LLM 호출 없음·명시적 분석 버튼·실패 입력·수정/삭제 및 build 통과.

## 구현

- 최신 검색·섭취량 UI: 결과 더블클릭/Enter 또는 선택 후 적용으로 음식 항목을 반영한다. 기존 항목 교체 시 중복 추가하지 않고 후보/신뢰도/결과 목록을 닫는다. 섭취량은 1인분 기본, ±0.5 및 직접 입력이며 화면의 g/ml 선택은 제거했다. 실제 기준량은 DB에 유지하고 인분에 맞춰 서버가 영양을 재계산한다. 간단한 영양 요약만 노출하고 상세 영양 수정은 접힌 메뉴로 제공한다.

- 사용자 후속 UI 결정: 기본은 **사진 선택 → 「사진 분석하기」 버튼 → YOLO 분석**. 사진 선택 시 자동 분석하지 않는다. 최초 화면에서는 검색/직접 입력을 숨기고 인식 실패 시 검색 및 빈 입력 항목을 자동으로 연다. 정상 인식 후에도 「음식 추가·변경」으로 대체 입력에 진입할 수 있다. LLM은 자동 호출하지 않으며 직접 입력 항목의 「영양 정보를 모르겠어요」 보조 메뉴에서 사용자가 버튼을 누르고 전송 동의까지 한 경우에만 호출한다. 「사진만 저장」은 사진 기록 옵션으로 옮겼다. 직접 입력/삭제 버튼 및 카드/폼 간격을 PC·모바일에 맞춰 정리했다.

- `POST /meals/detect?analyze=false`: 이미지 유효성·소유권·비공개 저장을 유지하며 모델을 호출하지 않는다. 사진 ID로 빈 항목 식단을 저장할 수 있다.
- 기본 detect: 추론 오류/빈 탐지를 HTTP 200, `analysis_status=failed`, 빈 목록으로 반환하고 사진을 보존한다. 이미지 형식·크기, 저장소/DB 오류는 기존 오류 응답을 유지한다.
- 탐지별 confidence 및 실제 YOLO head 점수의 Top-3를 반환한다. 원본 박스와 IoU 0.5 이상인 anchor에서만 후보를 제공한다. 모델 출력 형식이 지원되지 않으면 후보를 만들지 않는다. `MEAL_LOW_CONFIDENCE_THRESHOLD=0.5`는 조정 가능한 개발 기본값이다.
- `GET /foods/search?q=...`: 기존 음식과 식약처 별도 카탈로그의 부분 일치 검색. 제공량·영양·출처를 반환한다. g/ml는 원본 단위를 유지한다.
- `POST /foods/portion`: 검색 음식의 양에 따른 서버 영양 미리보기. g/ml를 임의 변환하지 않는다.
- `POST /foods/estimate`: 음식명·양·단위 및 명시적 외부 AI 전송 동의 필수. 기존 Coach의 `OPENAI_API_KEY`, `OPENAI_MODEL`, `OPENAI_BASE_URL`, timeout 재사용. JSON 출력·유한 숫자·음수·상한·불리언을 검증한다. 공급자 장애·잘못된 출력은 빈 영양값으로 돌아가 직접 입력/기록이 가능하다.
- `POST /meals`: 검색·직접 입력·사진만 저장을 지원한다. 영양 미입력은 null, 검색 영양 계산은 서버에서 수행하며 사용자 확인 수정값을 저장한다.
- `PATCH /meals/{id}`: 날짜·식사 구분·시간·사진·음식/양·영양값 수정 및 항목 추가/삭제. 생략 필드는 보존한다. 식단 expected_version과 기존 항목 version을 검사한다. 항목 출처·원본 탐지는 보존하고 수정 여부를 기록한다.
- 사진 교체/제거는 참조만 변경한다. 기존 원본·공개 사본의 물리 삭제, 식단 전체 삭제, 보상 재지급/회수 정책은 추가하지 않는다. 기존 보상 생성 훅·사진 해시 중복 검사는 유지한다.
- 히스토리에서 영양 정보 입력 필요/AI 추정값 표시 및 전체 수정. 직접 수정한 영양값은 기존 CSV 기반 섭취비율 수정으로 덮어쓰지 않도록 전체 수정으로 안내한다.

## 실제 데이터

사용자 제공 원본: 프로젝트 루트 `20260828_음식DB_19617건.xlsx`.

공식 배포처: <https://various.foodsafetykorea.go.kr/nutrient/general/down/historyList.do>.

전체 19,617행 검증 및 격리 SQLite 적재·조회 성공. 순대국/순댓국 부분 검색 일치 8행. 영양 기준량은 100g 13,877행, 100ml 5,740행이다. 같은 단위의 명시된 식품중량/제공량이 있으면 해당 제공량으로 서버 환산하고, 없으면 원본 기준량을 표시한다. 누락 수치는 null로 유지한다. 원본 파일·기존 CSV·class_id를 변경하지 않는다.

## 공유 Supabase 적용 결과

2026-11-01 사용자 명시 승인 「웅 적재후 재시작」으로 **이번 작업에 한해 작업 브랜치 적용을 예외 승인받아 완료했다.** Git push·merge 또는 향후 공유 DB 작업의 상시 승인을 의미하지 않는다.

- 적용 전 `20261031_01` 확인 후 meals 37건·meal_items 40건의 전체 데이터와 스키마를 Git 제외 `backups/meal-fallback-before-20261101-184702.json.gz`에 백업하고 다시 읽어 확인했다.
- migration `20261101_01` 적용 성공. 기존 37건·40건의 **모든 기존 필드**가 백업과 일치함을 적용 후 확인했다.
- `nutrition_foods` 19,617건 적재, 순대국 관련 8건 및 RLS 활성화를 Supabase에서 확인했다. 적재는 500행 단위 upsert를 단일 트랜잭션으로 수행했다.
- Backend를 최신 코드로 재시작했다. 프런트(5174), 그래프 health(8502), 프런트 프록시 DB health, 기존 음식 카탈로그 HTTP 200 확인.
- 자동 migration은 계속 false이며 실제 회원 식단을 새로 만들거나 수정하는 통합 테스트는 수행하지 않았다.

기본 [공유 DB 규칙](../operations/SUPABASE_SHARED_DB_GUIDE.md)은 그대로 유지한다. `RUN_MIGRATIONS_ON_START=false`를 유지하며, 공유 DB를 대상으로 PostgreSQL 자동 테스트를 실행하지 않는다.

검토할 파일:

- `backend/migrations/versions/20261101_01_meal_fallback.py`: 기존 기록의 분석 상태/출처 backfill, 음식 FK nullable, 새 상태/출처/제공량 필드, 식약처 별도 테이블 및 RLS. 기존 기록 삭제 없음. 새 수동 항목을 구버전으로 무손실 변환할 수 없어 자동 downgrade는 거부한다.
- `backend/scripts/import_nutrition_foods.py`: 기본은 검증만 수행하며 DB 접속 없음. `--apply`일 때만 식품코드 기준 upsert. 검증 실패가 있으면 쓰기를 거부한다.

재현 가능한 담당자 절차(이번에는 실행 완료. 다른 환경은 백업·현재 revision 확인 후):

```powershell
# 현재 checkout에 설치된 backend 가상환경 Python을 사용한다.
python -m pip install -r backend/requirements-dev.txt
python -m alembic -c backend/alembic.ini current
# 후속 migration이 있다면 담당자가 revision 연결을 먼저 조정한다.
python -m alembic -c backend/alembic.ini upgrade 20261101_01
python -m backend.scripts.import_nutrition_foods '20260828_음식DB_19617건.xlsx'
python -m backend.scripts.import_nutrition_foods '20260828_음식DB_19617건.xlsx' --apply
# 이어서 가이드대로 Backend 재시작. .env 비밀값은 출력/커밋하지 않는다.
```

이 작업 폴더는 인접 checkout의 `.venv-backend`를 재사용해 검증했다. 실행 문서의 Python 경로는 각 checkout의 설치 위치에 맞춘다. 실제 OpenAI 요청은 실행하지 않았으며 공급자 응답은 테스트에서 대체했다.

## 검증 근거

- Backend 전체: 커뮤니티 포인트 1/3/1, 커뮤니티 XP 전환 false의 명시적 테스트 설정에서 344통과·10제외·3실패. 실패 3건은 기존 추천 오류 응답의 `detail` 키 검사로, 변경 전 HEAD에서 같은 실패를 재현했다. 운영 `.env`는 수정하지 않았다.
- 새 API 검사는 격리 SQLite/로컬 이미지로 수행: 사진만 저장 후 보완, 전체 필드 수정, 항목 추가/삭제, 소유권, 동시 수정, 영양 범위/NaN 검증, OpenAI 장애 출력/동의, 실제 후보 전달, 출처 기록, 사진 교체/제거, g/ml 불일치 거부.
- 실제 web 모델에서 탐지 2건과 각 Top-3 반환 확인. mobile 모델은 같은 샘플에서 빈 탐지 정상 반환. 모델 파일은 변경하지 않았다.
- 원래 스키마에서 신규 migration을 격리 SQLite에 적용 검증. PostgreSQL DDL 생성 검증(실행 안 함). 실제 PostgreSQL migration 검증은 담당자 적용 전 별도 필요.
- 프런트 production build 성공. Vite 기존 큰 번들 경고는 남는다.
- Playwright: 1440px/390px에서 사진만 저장, 실패→검색→기록, 검색 없음→직접 입력(영양 미입력), OpenAI 추정 확인, 저신뢰 후보 선택, 전체 수정 시나리오 및 가로 넘침/JS 오류 없음. React fixture와 합성 API를 사용했으며 실제 Supabase·OpenAI·참가자 재테스트를 의미하지 않는다.

브라우저 재현:

```powershell
# Playwright와 설치된 Chromium/Edge 필요. Vite가 실행 중이어야 한다.
node frontend/tests/meal-recorder.browser.mjs
```

`PLAYWRIGHT_MODULE`로 임시 설치 모듈 경로, `PREVIEW_URL`로 Vite 주소를 지정할 수 있다. 화면만 검토하려면 `/tests/meal-recorder.html`을 연다(합성 데이터이며 실제 기록 안 됨). 스크린샷과 검증 DB는 Git에서 제외되는 `.runtime-logs`에 있다.

## 남은 완료 기준

- 실제 Supabase에서 본인 계정으로 사진 등록·편집, 실제 OpenAI 추정 응답, PC/모바일 통합 확인.
- 실제 순대국 사진 인식 실패부터 기록까지 및 참가자 재테스트. 모델 정확도 개선/클래스 확대/재학습/Coach 기능 확장은 하지 않았다.

## 발표용 문안: 사용자 테스트 → 개선

발견한 문제: 인식 실패 시 기록 불가 · 사진만 저장 불가 · 일부 항목 수정 불가.

인사이트: 인식 정확도뿐 아니라 실패했을 때의 대체 동선이 필요했다.

개선: AI Detection → Search → Manual Input → Record. 사진만 저장 후 영양 보완과 전체 항목 수정을 지원한다.

결과 표기: 현재는 구현·격리 검증 단계이며, 실제 참가자 재테스트 결과는 확인 후 추가한다.
