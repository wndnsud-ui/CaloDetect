# CaloDetect — Codex 통합 개발 업무지시서 v11
> 내부 프로젝트 버전: CaloDetect 2.0  
> 기준일: 2026-10-02  
> 전제: 팀원 3명 / 개발 기간 3주 / 웹앱 한정  
> 용도: Codex 개발 작업 지시 / 팀 공통 개발 기준 / 프로젝트 Master Spec  
> 변경 이력: `CHANGELOG.md` 참고 (본문은 현재 기준만 기술)

---

# 1. 문서 목적

본 문서는 기존 CaloDetect 프로젝트를 기반으로 기능을 보완·확장하기 위한 **통합 개발 업무지시서**다.

사용자에게 노출되는 서비스명은 다음과 같이 통일한다.

```text
서비스명: CaloDetect
한글명: 칼로디텍트
```

`CaloDetect 2.0`이라는 표현은 다음 용도로만 사용한다.

```text
내부 프로젝트 버전명
회의 문서
GitHub 문서
개발 버전 구분
발표에서 기존 버전과 비교할 때
```

사용자 화면에는 원칙적으로 `CaloDetect`만 표시한다.

---

# 2. 프로젝트 핵심 방향

기존 CaloDetect는 다음 흐름을 중심으로 한다.

```text
음식 사진
→ 음식 탐지
→ 사용자 보정
→ 기존 영양정보 조회
→ 영양정보 계산
→ 식단 기록
→ 대시보드
```

이번 프로젝트에서는 이 기존 흐름을 유지하면서 다음 기능을 추가한다.

```text
식단 기록
→ 오늘의 영양 상태 분석
→ 남은 섭취 상태 계산
→ 식사 후보 추천
→ 추천 이유 제공
→ 사용자 선택 및 기록
```

중요:

> CaloDetect는 단순 음식 이미지 탐지 프로그램이 아니라  
> 사용자의 음식 기록과 영양 데이터를 실제 다음 선택까지 연결하는 웹 서비스로 확장한다.

---

# 3. 최우선 개발 원칙

## 기존 프로젝트 재사용

기존 프로젝트를 새로 만들거나 전체 구조를 갈아엎지 않는다.

먼저 현재 Repository를 분석하고 다음을 구분한다.

```text
REUSE
MODIFY
NEW BUILD
DO NOT TOUCH
```

### REUSE 우선 대상

- 기존 YOLO 음식 탐지 코드
- 학습된 모델
- 기존 음식 클래스
- YAML
- CSV
- 기존 음식·영양 데이터 연결 구조가 이미 존재하면 그대로 재사용
- 영양 계산 로직
- 사용자 음식명 수정 기능
- 식단 기록 기능
- 기존 Streamlit
- 기존 데이터 정제 결과
- 기존 실험 결과

---

# 4. 절대 금지 사항

Codex는 다음을 임의로 수행하지 않는다.

1. Repository 전체 재작성
2. 기존 동작 코드 대규모 삭제
3. 기존 모델 파일 덮어쓰기
4. 기존 CSV/YAML 원본 덮어쓰기
5. 기존 음식·영양 데이터 연결 구조 임의 변경
6. 신규 Nutrition key / 매핑 규칙 임의 설계
7. Streamlit 삭제
8. LLM으로 영양 수치 직접 계산
9. API Key를 Client에 노출
10. 비밀번호 평문 저장
11. 새로운 Framework 임의 도입
12. P0 완료 전 확장 기능 선행 구현
13. 사용자 correction을 검수 없이 바로 학습 데이터로 사용
14. candidate 모델을 검증 없이 production으로 교체
15. 음식 섭취 칼로리를 운동으로 단순 상쇄하는 추천
16. 식단·영양 결과를 의료 진단처럼 표현
17. 근거 없는 일반 식당 영양 수치 생성
18. Phase 2 이후 기능을 "확장 가능성"을 이유로 미리 구현

---

# 5. 현재 팀 확정 기술 구조

## Backend

```text
FastAPI
Python
SQLAlchemy
Pydantic
Alembic
PostgreSQL
```

## Frontend

```text
React
```

사용자 서비스는 웹앱으로 한정한다.

현재 프로젝트 범위에서 React Native / Expo 기반 모바일 앱을 새로 개발하지 않는다.

## 관리자 / QA / 분석

```text
Streamlit
```

기존 Streamlit은 삭제하지 않고 다음 용도로 전환 또는 재사용한다.

- 관리자 QA
- 데이터 검수
- `CaloDetect_nutrition_all_matched(1).csv` 데이터 검수
- 모델 모니터링
- 사용자 correction 검수
- 재학습 후보 관리
- 통계 확인

## Vision

```text
YOLO26m
```

## DB

```text
PostgreSQL
```

## AI 역할

```text
Python / DB = 계산
LLM = 설명
```

### 확장 대비 원칙

현재 P0에서 별도 챗봇을 구현하지 않는다.

다만 향후 챗봇이나 자연어 입력을 추가해도 추천엔진을 다시 만들 필요가 없도록,
추천 기능은 **독립된 서비스 함수/API**로 설계한다.

```text
get_today_status()
recommend_meals(filters)
```

향후 P1에서 필요하면 다음과 같은 함수가 추가될 수 있다.

```text
simulate_meal()
log_meal()
```

중요:

- 챗봇이 계산하지 않는다.
- 챗봇은 위 함수가 반환한 계산 결과를 설명하거나 조건을 전달하는 얇은 레이어로만 사용한다.
- 현재 P0에는 챗봇 UI/대화 저장/Tool Calling 구현을 포함하지 않는다.

---

# 6. 아직 팀 결정이 필요한 항목

Codex는 아래 항목을 임의로 확정하지 않는다.

```text
[TBD] 추천 메뉴 데이터 최종 출처
[TBD] 추천 Score 초기 가중치
[TBD] goal_type별 탄단지 목표 비율
[TBD] 당류 참고 기준
[TBD] 나트륨 참고 기준
[TBD] 업로드 이미지 저장 위치
[TBD] 이미지 보관 기간
[TBD] 모델 개선용 이미지 활용 동의 문구
[TBD] 가입 연령 하한
[TBD] 인증 방식 세부 구현
[TBD] LLM 공급자 / 모델
[TBD] 배포 대상
[TBD] 재학습 Trigger N 값
[TBD] 식사 추천 API에서 이번 P0에 실제 노출할 조건 필터 범위
[TBD] 최근 음식 반복 Penalty 기준 끼니 수 N
```

### 1주차 안에 반드시 결정할 항목

- 추천 메뉴 데이터 출처
- 추천 Score 초기값
- 탄단지·당류·나트륨 기준
- 사진 저장 정책
- 가입 연령 정책

결정되지 않은 항목은 `TBD`로 유지하며 Codex가 임의로 채우지 않는다.

# 7. Repository 루트 `AGENTS.md` 생성

Codex가 작업할 때마다 자동으로 참조할 수 있도록 Repository 루트에 `AGENTS.md`를 만든다.

최소 규칙:

```text
- 기존 프로젝트 전체 재작성 금지
- 기존 파일 덮어쓰기 금지
- 관련 없는 파일 대규모 수정 금지
- P0 우선
- TBD 임의 결정 금지
- Python/DB = 계산
- LLM = 설명
- 사용자 Correction은 QA 후 사용
- 변경 후 테스트
- README와 실제 실행법 일치
```

---

# 8. Codex 최초 작업 순서

Codex는 바로 기능 구현을 시작하지 않는다.

## STEP 1. Repository 분석

전체 폴더 구조 확인:

```text
backend/
frontend/
streamlit/
models/
data/
experiments/
tests/
docker/
README
requirements
.env.example
```

실제 구조가 다르면 현재 Repository 기준으로 기록한다.

## STEP 2. 기존 자산 목록화

다음 파일과 기능을 확인한다.

### 모델

- YOLO26m 결과
- best.pt
- last.pt
- args.yaml
- results.csv
- confusion matrix
- PR curve
- F1 curve

### 데이터

- `data.yaml`
- 음식 클래스
- 현재 약 150종 음식 클래스
- **영양성분 기준 파일: `CaloDetect_nutrition_all_matched(1).csv`**
- 기존 음식·영양 연결용 CSV가 추가로 존재하면 보존하되, 신규 매핑 규칙 설계는 현재 범위에서 제외
- serving 기준
- default grams

#### 영양성분 Source of Truth

이번 P0에서 영양정보 조회 및 계산의 기준 파일은 아래 하나로 고정한다.

```text
CaloDetect_nutrition_all_matched(1).csv
```

Codex는 임의로 다른 영양 CSV를 기준 데이터로 선택하지 않는다.

기존 코드가 다른 영양 파일을 사용 중이면 즉시 갈아끼우지 말고:

```text
현재 참조 파일 확인
→ CaloDetect_nutrition_all_matched(1).csv과 컬럼/값 비교
→ 호환성 확인
→ 변경 필요 시 IMPLEMENTATION_PLAN.md에 기록
```

순서로 처리한다.

원본 CSV의 값과 컬럼을 임의 수정하지 않는다.

### 서비스

- 이미지 업로드
- YOLO 분석
- 음식명 수정
- 영양값 계산
- 식단 저장
- 대시보드
- Streamlit
- 기존 DB

## STEP 3. 기존 기능 직접 실행

실제 실행으로 확인한다.

```text
사진 업로드
→ 탐지
→ 음식명 출력
→ 사용자 수정
→ 영양정보 조회
→ 영양 계산
→ 저장
→ 조회
```

작동 여부를 추측하지 않는다.

## STEP 4. 문서 먼저 작성

다음 문서를 우선 생성한다.

```text
AGENTS.md
IMPLEMENTATION_PLAN.md
ARCHITECTURE.md
DATA_SCHEMA.md
MODEL_EXPERIMENTS.md
ROADMAP.md
CHANGELOG.md
CHANGELOG.md
```

---

# 9. IMPLEMENTATION_PLAN.md 필수 내용

다음 항목을 반드시 포함한다.

```text
현재 구현 기능
재사용 가능 기능
수정 필요 기능
신규 구현 기능
삭제 금지 기능
P0
P1
Backlog
현재 DB 상태
현재 API 상태
모델 상태
작업 순서
테스트 계획
리스크
TBD 항목
```

Codex는 이 문서를 먼저 생성한 후 기능 개발에 들어간다.

## CHANGELOG.md 관리 규칙

Master Spec 본문은 **현재 유효한 기준만** 유지한다.

이후 팀 결정이나 구현 기준이 바뀌면 본문에 과거 문구를 중첩해 쌓지 말고 `CHANGELOG.md`에 기록한다.

형식:

```text
날짜
변경 항목
변경 전
변경 후
변경 이유
영향 범위
```

예:

```text
2026-10-02
항목: 추천 반복 Penalty
변경 전: TBD
변경 후: recent_meal_window = 3 (development_default)
이유: Demo 개발 기본값 필요
영향: recommendation config
```

---

# 10. 사용자 전체 Flow

이번 3주 프로젝트의 완료 시나리오는 아래로 제한한다.

```text
회원가입
→ 로그인
→ 프로필 입력
→ 목표 칼로리 설정
→ 홈
→ 음식 사진 업로드
→ YOLO 음식 탐지
→ 음식명 확인/수정
→ 섭취량 입력
→ 영양정보 계산
→ PostgreSQL 저장
→ 오늘 영양 상태 확인
→ 식사 추천
→ 추천 메뉴 3개 확인
→ Rule 기반 추천 이유 확인
→ History 확인
→ 로그아웃
→ 재로그인
→ 기존 기록 유지
```

오탐 발생 시:

```text
사용자 수정
→ Correction 저장
→ 모델 개선 활용 동의 확인
→ Streamlit 관리자 QA
→ 승인/거절
→ 승인 샘플 누적
```

**실제 재학습 실행은 P1이다.**

# 11. 회원 시스템

P0는 이메일 회원가입/로그인을 우선한다.

## 기능

- 회원가입
- 로그인
- 로그아웃
- 사용자별 데이터 분리
- 재로그인 후 기록 유지

## users

```text
id
email
password_hash
oauth_provider
oauth_subject
role
model_improvement_consent
model_improvement_consent_at
created_at
updated_at
```

`role` 값:

```text
user
admin
```

기본값은 `user`다.

`/admin/*` API는 반드시 `admin` 역할만 접근할 수 있게 한다.
일반 사용자가 `/admin/*` API를 호출하면 `403 Forbidden`을 반환한다.

P0에서는 이메일 인증을 우선한다.

소셜 로그인은 P1이지만 향후 도입 시 `(oauth_provider, oauth_subject)`를 고유 식별자로 사용할 수 있도록 스키마를 고려한다. 소셜 가입 계정은 `password_hash` nullable 여부를 검토한다.

## 보안

- Password Hash 필수
- Secret은 `.env`
- API Key는 Backend 관리
- Client 노출 금지
- 사용자별 Resource Authorization 적용

# 12. 사용자 Profile

최소 필드:

```text
height
weight
age
sex
activity_level
goal_type
```

goal_type:

```text
weight_loss
maintain
muscle_gain
```

저장 또는 계산:

```text
bmr
tdee
minimum_calories
recommended_calorie_min
recommended_calorie_max
target_calories
target_carbs
target_protein
target_fat
target_sugar
target_sodium
```

사용자는 설정값을 나중에 수정할 수 있어야 한다.

# 13. 첫 관리자 계정 생성

`users.role`의 기본값은 반드시 `user`다.

일반 사용자에게 관리자 승격 API를 제공하지 않는다.

P0에서 최초 관리자 계정은 내부 운영 방식으로만 생성한다.

권장:

```text
1. seed script
2. CLI command
3. 배포 환경의 one-time bootstrap
```

예:

```bash
python scripts/create_admin.py --email admin@example.com
```

금지:

```text
POST /users/{id}/make-admin
공개 관리자 승격 버튼
일반 사용자가 role을 직접 수정
```

## Streamlit 관리자 인증

Streamlit QA 화면 역시 관리자 인증을 거친다.

```text
관리자 로그인
→ FastAPI 인증
→ access token 발급
→ Streamlit session에 token 보관
→ /admin/* 호출 시 Authorization header 전달
```

Streamlit이 관리자 인증을 우회하여 PostgreSQL을 직접 수정하지 않는다.

---

# 14. 개인정보 / 모델 개선 활용 동의

서비스 이용 동의와 모델 개선용 이미지 활용 동의를 분리한다.

```text
[필수] 서비스 이용 동의
[선택] 업로드 이미지를 모델 개선에 활용하는 것에 동의
```

사용자 단위 동의 상태는 `users`에 저장한다.

```text
model_improvement_consent
model_improvement_consent_at
```

미동의 사용자의 Correction은 서비스 기록으로 저장할 수 있으나, 재학습 후보에는 자동 등록하지 않는다.

### 동의 철회 정책

사용자가 모델 개선 활용 동의를 철회하면:

```text
향후 신규 Correction → Retraining Candidate 자동 등록 금지
기존 PENDING Retraining Sample → 제외 처리
```

이미 `APPROVED`되어 별도 Dataset으로 반영된 데이터의 처리 정책은 배포 전 별도 확정한다.

동의 철회 자체로 식단 기록이나 Correction 이력을 삭제하지 않는다.

이미지 보관기간, 실제 동의 문구, APPROVED 이후 데이터 처리 정책은 `TBD`다.

## 연령 정책

현재 BMR/TDEE 및 최소 칼로리 로직은 성인 사용을 전제로 한다.
가입 연령 하한은 팀이 확정해야 한다.

```text
AGE_MIN = TBD
```

Codex가 임의 숫자를 설정하지 않는다.

---

# 15. 목표 칼로리 계산

현재 회의 기준.

## BMR

Mifflin-St Jeor.

남성:

```text
10 × weight(kg)
+ 6.25 × height(cm)
- 5 × age
+ 5
```

여성:

```text
10 × weight(kg)
+ 6.25 × height(cm)
- 5 × age
- 161
```

## TDEE

```text
TDEE = BMR × Activity Factor
```

현재 기준:

```text
sedentary = 1.2
light = 1.375
moderate = 1.55
active = 1.725
```

## 최소 허용값

```text
minimum_calories = max(BMR, absolute_minimum)
```

회의 기준:

```text
female = 1200 kcal
male = 1500 kcal
```

## 목표별 권장 범위

### 감량

```text
TDEE - 750 ~ TDEE - 300
default = TDEE - 500
```

### 유지

```text
TDEE ± 100
```

### 증가

```text
TDEE + 300 ~ TDEE + 500
```

권장 범위 하단이 minimum보다 낮으면 minimum으로 올린다.

## 사용자 입력 상한

```text
5000 kcal
```

### UX

| 사용자 입력 | 처리 |
|---|---|
| minimum 미만 | 저장 불가 |
| 5000 초과 | 저장 불가 |
| minimum 이상, 권장범위 미만 | 저장 가능 + 안내 |
| 권장 범위 | 정상 저장 |
| 감량 목표인데 권장범위 초과 | 저장 가능 + 안내 |

주의:

이 값과 기준은 현재 팀 회의 기준이다.

발표 또는 실제 배포 전에 기준 출처를 다시 검토한다.

---

# 16. 음식 분석

## Flow

```text
이미지 업로드
→ YOLO26m
→ predicted_label
→ confidence
→ 사용자 확인
→ corrected_label
→ canonical food
→ 기존 영양 데이터 조회
→ 섭취량 적용
→ Python 영양 계산
→ PostgreSQL 저장
```

## Detection 실패

탐지가 실패하더라도 사용자는 계속 진행할 수 있어야 한다.

```text
[음식 직접 선택]
```

경로를 반드시 제공한다.

---

# 17. 음식·영양 데이터 연결 원칙

현재 MVP에서는 **새로운 DB 매핑 규칙을 설계하거나 고도화하지 않는다.**

원칙:

- 기존 프로젝트에 이미 음식과 영양 데이터가 연결되어 있으면 그대로 재사용한다.
- 현재 서비스 흐름에 필요한 수준의 조회만 유지한다.
- 신규 key 체계, 복잡한 매핑 테이블, 자동 매핑 규칙 설계는 현재 P0에서 제외한다.
- 기존 데이터 구조를 깨뜨리지 않는다.
- 연결이 되지 않는 데이터는 예외 로그로 남기고 수동 확인 가능하게 한다.

향후 확장 서비스에서 필요할 경우 아래를 별도 설계한다.

```text
canonical food mapping
nutrition key 정책
유사 음식 자동 매칭
외부 음식 DB 연동
매핑 테이블 버전 관리
```

이 항목은 현재 `ROADMAP.md` 관리 대상으로 본다.

---

# 18. Food Master

현재 음식 데이터를 우선 분석하고, 신규 매핑 체계를 만들지 않는다.

현재 MVP에서 우선 관리할 필드:

```text
canonical_name
display_name
model_class
category
subcategory
serving_unit
default_grams
nutrition_source  # 기본 기준: CaloDetect_nutrition_all_matched(1).csv
active
```

`active/status` 중 본 문서 기준 상태 필드는 `active`로 통일한다.

기존 프로젝트에서 `nutrition_key`를 이미 사용하고 있다면 그대로 보존할 수 있다. 단, 새로운 `nutrition_key` 정책은 만들지 않는다.

# 19. 추천 후보 메뉴 Master — P0 데이터 작업

추천 엔진 구현 전에 가장 먼저 기존 음식 DB를 검사한다.

순서:

```text
현재 음식 DB 확인
→ 추천 가능한 음식 수 확인
→ 1회 섭취 기준 확인
→ 영양값 존재 여부 확인
→ 추천 후보로 재사용 가능한지 판단
```

### 기존 DB가 충분한 경우

기존 데이터를 그대로 사용한다.

### 부족한 경우

최소한의 `recommendation_menu_master`만 추가한다.

예:

```text
menu_id
menu_name
category
meal_type
serving_unit
default_grams
calories
carbs
protein
fat
sugar
sodium
source
active
```

Codex가 예시 메뉴를 임의 하드코딩해서 후보 목록을 만들지 않는다.
영양값 출처가 없는 메뉴는 정량 Ranking에 사용하지 않는다.

추천 메뉴 데이터의 최종 출처는 **1주차 필수 결정사항**이다.

# 20. 식단 기록 영구화

## meals

```text
id
user_id
meal_date
meal_type
created_at
```

## meal_items

```text
id
meal_id
food_id
detection_log_id   # nullable, 수동 선택 음식은 null
predicted_label
corrected_label
confidence
serving_multiplier
calculated_calories
calculated_carbs
calculated_protein
calculated_fat
calculated_sugar
calculated_sodium
created_at
```

영양 계산은 Python이 담당한다.

LLM은 수치를 계산하지 않는다.

---

# 21. 오늘 상태 분석

Home에서 최소 제공:

```text
오늘 섭취 Calories / 목표
남은 Calories
Carbs
Protein
Fat
Sugar
Sodium
끼니별 기록
상태 안내 문장
```

Python이 계산한다.

P0에서는 Rule 기반 안내 문장으로 충분하다.

예:

```text
현재 단백질 섭취량이 목표보다 부족합니다.
남은 칼로리 범위 안에서 단백질을 보완할 수 있는 식사를 추천합니다.
```

## 날짜 기준

서비스의 사용자 날짜 기준은 다음으로 통일한다.

```text
Asia/Seoul
```

UTC timestamp를 저장하더라도 `오늘 식단`, `meal_date`, 일일 합계, History, 추천 snapshot은 KST 기준으로 계산한다.

필수 경계 테스트:

```text
23:59 KST 저장
00:01 KST 저장
```

두 기록이 서로 다른 날짜로 집계되는지 확인한다.

# 22. 식사 추천 엔진

사용자에게는 단순하게 `식사 추천` 기능으로 표시한다.

예:

```text
[식사 추천]
```

또는:

```text
[추천 보기]
```

브랜드 메시지를 버튼에 억지로 넣지 않는다.

## 입력

```text
goal_type
target_calories
오늘 누적 calories
남은 calories
carbs
protein
fat
sugar
sodium
meal_type
recent meals
preference
exclude foods
```

---

# 23. 추천 엔진 단계

## Python Filter

후보 메뉴 중 다음 기준으로 1차 필터.

```text
남은 칼로리
단백질 부족량
당류 상태
나트륨 상태
탄단지 상태
끼니
제외 음식
선호
```

---

# 24. 추천 Score 규칙

이번 MVP에서는 복잡한 최적화보다 설명 가능한 Rule-Based Ranking을 사용한다.

기본 순서:

```text
1. 제외 조건 적용
2. 남은 칼로리 범위 확인
3. 부족 영양소 보완 정도 계산
4. 당류/나트륨 조건 확인
5. 끼니 적합성 확인
6. 최근 음식 반복 Penalty
7. 유사 메뉴 다양성 조정
8. Top 3
```

Score 형태가 필요하면 아래와 같은 구조를 사용할 수 있다.

```python
score = (
    calorie_fit
    + protein_fit
    + macro_fit
    + sugar_fit
    + sodium_fit
    + meal_fit
    + preference_fit
    - repeat_penalty
)
```

실제 초기 가중치는 팀이 확정한다.

```text
RECOMMENDATION_WEIGHTS = TBD
```

### Week 1 종료 시까지 가중치가 미확정인 경우

Demo 개발이 막히지 않도록 `development_default`를 사용한다.

```yaml
development_default:
  calorie_fit: 1.0
  protein_fit: 1.0
  macro_fit: 1.0
  sugar_fit: 1.0
  sodium_fit: 1.0
  meal_fit: 1.0
  preference_fit: 1.0
  repeat_penalty: 1.0
  recent_meal_window: 3
```

이 값은 개발/데모용 초기값이며 최종 서비스 정책값으로 간주하지 않는다.
최종 가중치는 config에서 교체 가능해야 한다.

### 다양성

Top 3가 지나치게 유사하지 않도록 후처리한다.

### 반복 Penalty

최근 N끼 내 동일/유사 음식은 감점할 수 있다.

```text
RECENT_MEAL_WINDOW = TBD
```

N은 config로 관리한다. Week 1까지 미결정이면 `development_default` 값을 사용하되 데모용 값임을 명시한다.

# 25. 추천 결과

P0에서는 항상 3개를 반환한다.

```text
메뉴명
예상 영양 구성
추천 기준
Rule 기반 추천 이유
```

내부 Score는 로그/디버깅용으로만 저장한다.

사용자 화면에는 다음처럼 이유를 보여준다.

```text
- 남은 섭취량 범위에 적합
- 단백질 보완에 유리
- 최근 식사와 중복이 적음
```

기본 UI에서 `추천점수 87점` 같은 숫자는 노출하지 않는다.

영양값이 실제 데이터에 존재하는 후보만 정량 표시한다.

## recommendation_logs.acted 정의

P0에서는 다음으로 정의한다.

```text
추천된 메뉴를 사용자가 실제 식단 기록으로 저장한 경우 = acted = true
```

단순 클릭/상세보기는 acted로 처리하지 않는다.

# 26. LLM 역할 — P1

LLM 연동은 P0가 아니다.

P0는 Rule 기반 추천 이유로 완성한다.

P1에서 LLM은 다음만 담당한다.

- 현재 상태 자연어 요약
- 추천 이유 표현 개선
- 사용자 질문에 대한 설명

LLM은 Calories, 탄단지, BMR/TDEE, Recommendation Score를 계산하지 않는다.

# 27. LLM 장애 Fallback — P1

LLM 도입 이후에도 핵심 추천 결과는 Python이 생성한다.

```text
Python Recommendation
→ Top 3
→ LLM 오류
→ Rule 기반 reason 유지
```

따라서 LLM 장애가 추천 기능 전체 실패로 이어지면 안 된다.

# 28. Recommendation API 확장성

챗봇을 지금 별도 핵심 기능으로 만들 필요는 없다.

대신 Recommendation API가 조건을 받을 수 있도록 설계한다.

예:

```json
{
  "meal_type": "dinner",
  "budget": null,
  "place_type": null,
  "exclude_foods": [],
  "preferred_categories": []
}
```

향후:

```text
편의점밖에 없어
만원 이하로
포케 말고
```

등의 조건을 전달할 수 있게 한다.

현재는 API 구조만 확장 가능하게 만든다.

---

# 29. Menu Vision — P1

P0 완료 후 진행.

Flow:

```text
메뉴판 이미지
→ OCR / Vision
→ 메뉴명 후보
→ Menu Master 유사도 Matching
→ 실패 시 Category Rule
→ Recommendation Engine
→ 3개 추천
```

## 1차 Matching

```text
메뉴 Master와 문자열 / 유사도 Matching
```

## 2차 Fallback

Matching 실패 시:

```text
구이
찌개
볶음
면
밥
샐러드
```

등 Category 특성을 이용해 적합도만 판단한다.

영양 DB에 없는 메뉴의 kcal을 임의 생성하지 않는다.

---

# 30. 운동 추천 — P1

운동 추천은 이번 P0에서 제외한다.

이유:

```text
운동 DB
활동 데이터
시간
장비
실내/실외
컨디션
MET
```

등 별도 입력과 설계 범위가 커서 3주 MVP 핵심 Flow를 방해할 수 있다.

향후 구현 시에도 음식 섭취 칼로리를 운동으로 단순 상쇄하는 방식은 사용하지 않는다.

# 31. 운동 DB — P1

운동 추천을 구현하게 될 경우 별도 데이터 설계로 진행한다.
현재 P0에서 테이블/API/빈 파일을 미리 만들지 않는다.

# 32. 재학습 기능 — 이번 P0의 범위

이번 P0는 **실제 재학습 실행이 아니라 승인 샘플 누적까지** 구현한다.

```text
사용자 Correction
→ 모델 개선 활용 동의 확인
→ retraining_samples PENDING 등록
→ Streamlit QA 대기열 표시
→ 승인 / 거절
→ APPROVED 샘플 누적
```

YOLO 재학습을 sklearn `partial_fit()`처럼 직접 구현하지 않는다.

# 33. Detection / Correction 저장 흐름

Correction 저장 시점을 아래처럼 고정한다.

## 1단계 — 음식 탐지

```text
POST /meals/detect
→ YOLO26m 추론
→ Bounding Box별 detection_log 생성
→ predicted_label / confidence / bbox / model_version 저장
→ detection_id 목록 반환
```

원칙:

```text
Bounding Box 하나 = detection_logs 한 행
한 이미지에서 여러 음식 탐지 가능
```

## 2단계 — 식단 저장

```text
POST /meals
```

요청의 각 `meal_item`에 해당 `detection_id`를 포함한다.
탐지 실패 후 `[음식 직접 선택]`으로 추가한 음식은 `detection_id`를 null로 보낸다.

각 meal_item 단위로 아래를 처리한다.

```text
corrected_label == predicted_label
→ Correction 없음
→ Meal 저장

corrected_label != predicted_label
→ 같은 DB Transaction에서 detection_log.corrected_label 갱신
→ Meal 저장
→ model_improvement_consent == true 이면
   retraining_samples에 PENDING 등록
```

가능하면 Meal 저장과 Correction 갱신을 **동일 Transaction**으로 처리한다.

## detection_logs

```text
id
user_id
image_path
image_group_id
predicted_label
corrected_label
confidence
bbox_x1
bbox_y1
bbox_x2
bbox_y2
model_version
created_at
```

사용자가 수정하지 않았으면 `corrected_label`은 nullable 가능하다.

동의 상태는 사용자 단위 `users.model_improvement_consent`를 기준으로 판단한다.

### 저장 후 Correction 재수정 API

```text
POST /detections/{id}/correction
```

은 식단 저장 이후 사용자가 Correction을 다시 수정할 때 사용하는 보조 API다.

이 API에서도 사용자 동의 상태와 `retraining_samples` 상태를 함께 동기화한다.

# 34. 재학습 Candidate

사용자 Correction을 즉시 학습 데이터로 사용하지 않는다.

```text
Correction
→ consent 확인
→ retraining_samples PENDING 등록 (= 관리자 QA 대기열)
→ Streamlit QA
→ APPROVED / REJECTED
→ APPROVED 샘플만 향후 재학습 Dataset 후보
```

`PENDING`은 관리자 QA 대기 상태를 의미한다.

## retraining_samples

```text
id
detection_log_id
image_path
predicted_label
corrected_label
qa_status
approved_by  # admin user id
created_at
```

상태:

```text
PENDING
APPROVED
REJECTED
```

미동의 사용자의 이미지는 Retraining Candidate로 등록하지 않는다.

# 35. Streamlit 관리자 QA

P0 화면:

```text
이미지
기존 예측
사용자 수정
confidence
[승인]
[거절]
```

### 접근 방식

Streamlit이 PostgreSQL을 직접 수정하지 않는다.

```text
Streamlit Admin QA
→ FastAPI /admin/* API
→ 관리자 권한 검사
→ Service
→ PostgreSQL
```

이 구조로 권한·검증·로그를 Backend에 집중한다.

### 관리자 권한

```text
users.role == admin
```

인 사용자만 `/admin/*` API에 접근할 수 있다.

일반 사용자는:

```text
403 Forbidden
```

을 반환한다.


## APPROVED 샘플 재수정 정책

사용자가 식단 저장 이후 Correction을 다시 수정했는데,
기존 `retraining_samples`가 이미 `APPROVED` 상태인 경우 기존 행을 덮어쓰지 않는다.

처리:

```text
기존 APPROVED sample
→ 그대로 보존

새 Correction
→ 새 retraining_samples PENDING 생성
→ 관리자 재검수
```

이유:

- 이미 승인된 학습 데이터의 이력 보존
- 누가 언제 어떤 라벨을 승인했는지 추적 가능
- 과거 Dataset 재현 가능성 유지

기존 APPROVED 샘플을 자동 삭제하거나 자동 변경하지 않는다.

---

# 36. 실제 재학습 — P1

향후 구조:

```text
승인 샘플 N개
→ 기존 Dataset에 추가
→ 기존 Weight에서 추가 학습
→ Candidate Model
→ 동일 Test Set 평가
→ Production 비교
→ 승인
→ Production 승격
```

`RETRAIN_THRESHOLD = TBD`.

# 37. Model Registry / Promote / Rollback — P1

아래는 이번 P0 구현 대상이 아니다.

```text
model_registry
/admin/retraining/run
/admin/models
/admin/models/{id}/promote
/admin/models/{id}/rollback
```

Architecture/ROADMAP으로만 남긴다.

# 38. 현재 모델 기준

회의 결과 기준:

```text
YOLO26m
imgsz = 640
batch = 16
max epochs = 50
early stopping patience = 10
```

변경 시 `MODEL_EXPERIMENTS.md`에 근거를 기록한다.

# 39. 모델 평가 기준 — 향후 Candidate 평가용

- mAP50
- mAP50-95
- Precision
- Recall
- F1
- inference speed
- model size
- confusion matrix
- 실제 오탐/미탐
- 혼동 class pair
- 기존 영양정보 조회 성공 여부
- 전체 식단 저장 성공률

매핑 고도화가 현재 범위에서 제외되어 있으므로 별도의 신규 매핑 성능지표는 구현하지 않는다. 서비스 검증에서는 기존 영양정보 조회 성공 여부만 확인한다.

# 40. 모델 파일 관리 — P1 기준

모델 파일은 서로 덮어쓰지 않는다.

```text
models/
├── production/
├── candidate/
└── archive/
```

# 41. Rollback — P1

Production 교체 후 문제가 생겼을 때 이전 모델로 되돌릴 수 있는 구조를 향후 구현한다.

# 42. 실험 관리 원칙

기존 학습 결과는 보존한다. 동일 이름 `best.pt`로 계속 덮어쓰지 않는다.

# 43. 실험 폴더 규칙

```text
experiments/
├── EXP_001_yolo26m_baseline/
│   ├── runs/
│   ├── results_summary.md
│   └── notes.md
├── EXP_002_yolo26m_tuning/
│   ├── runs/
│   ├── results_summary.md
│   └── notes.md
└── EXP_003_yolo26m_service_validation/
    ├── service_test.csv
    ├── confusion_examples/
    └── validation_summary.md
```

보관:

```text
results.csv
results.png
confusion_matrix.png
confusion_matrix_normalized.png
PR_curve.png
F1_curve.png
P_curve.png
R_curve.png
val_batch*_pred.jpg
val_batch*_labels.jpg
weights/best.pt
weights/last.pt
args.yaml
```

---

# 44. 데이터 품질 점검

성능이 낮은 클래스는 추가 학습 전 먼저 확인한다.

```text
라벨 오류
클래스 불균형
유사 음식 혼동
train / val / test leakage
중복 이미지
저화질 이미지
Bounding Box 오류
영양정보 조회 오류
```

---

# 45. 최소 DB Schema

## users

```text
id
email
password_hash
oauth_provider
oauth_subject
role
model_improvement_consent
model_improvement_consent_at
created_at
updated_at
```

## user_profiles

```text
id
user_id
goal_type
height
weight
age
sex
activity_level
bmr
tdee
minimum_calories
recommended_calorie_min
recommended_calorie_max
target_calories
target_carbs
target_protein
target_fat
target_sugar
target_sodium
```

## foods

```text
id
canonical_name
display_name
model_class
category
subcategory
serving_unit
default_grams
nutrition_source  # 기본 기준: CaloDetect_nutrition_all_matched(1).csv
active
```

기존 프로젝트에서 `nutrition_key`가 이미 사용 중이면 보존 가능하지만 신규 정책은 만들지 않는다.

## nutrition

기존 영양 데이터 구조를 우선 재사용한다.

## meals

```text
id
user_id
meal_date
meal_type
created_at
```

## meal_items

```text
id
meal_id
food_id
detection_log_id   # nullable, 수동 선택 음식은 null
predicted_label
corrected_label
confidence
serving_multiplier
calculated_calories
calculated_carbs
calculated_protein
calculated_fat
calculated_sugar
calculated_sodium
created_at
```

## recommendation_logs

```text
id
user_id
generated_at
nutrition_snapshot
recommendation_json
selected_item
acted
```

## detection_logs

```text
id
user_id
image_path
image_group_id
predicted_label
corrected_label
confidence
bbox_x1
bbox_y1
bbox_x2
bbox_y2
model_version
created_at
```

## retraining_samples

```text
id
detection_log_id
image_path
predicted_label
corrected_label
qa_status
approved_by  # admin user id
created_at
```

`model_registry`, 운동 관련 테이블은 P1에서 필요 시 추가한다.

# 46. Backend 권장 구조

기존 구조를 우선 유지한다.

참고:

```text
backend/
├── app/
│   ├── main.py
│   ├── api/
│   │   ├── auth.py
│   │   ├── users.py
│   │   ├── meals.py
│   │   ├── analytics.py
│   │   ├── recommendations.py
│   │   ├── detection.py
│   │   └── admin_qa.py
│   ├── services/
│   │   ├── vision.py
│   │   ├── nutrition.py
│   │   ├── analytics.py
│   │   └── recommendation.py
│   ├── models/
│   ├── schemas/
│   ├── repositories/
│   ├── db/
│   └── core/
└── tests/
```

P1용 retraining / LLM / exercise 파일을 미리 빈 파일로 만들지 않는다.

# 47. 사용자 화면

서비스명:

```text
CaloDetect
```

`2.0`을 사용자 화면에 노출하지 않는다.

## Home

```text
CaloDetect

오늘 섭취
1,420 / 1,800 kcal

단백질
72 / 110 g

당류
현재 상태 표시

[음식 추가]
[식사 추천]
```

## Meal Scan

```text
사진 업로드
→ 분석
→ 음식 확인
→ 수정
→ 섭취량
→ 저장
```

## Recommendation

```text
현재 상태
추천 메뉴 3개
추천 이유
```

버튼:

```text
[식사 추천]
```

또는

```text
[추천 보기]
```

중 하나를 UI 디자인 단계에서 선택한다.

## History

```text
일별 식단
주간 식단
영양 패턴
```

## Statistics

```text
Calories
Carbs
Protein
Fat
Sugar
Sodium
```

## Profile

```text
사용자 정보
목표
Calories
탄단지
활동 수준
설정 수정
모델 개선 활용 동의 토글 (GET/PUT /users/me/consent)
```

동의 토글 OFF 시 동의 철회 정책(개인정보 / 모델 개선 활용 동의 섹션)을 따른다.

---

# 48. Homepage

사용자에게는 브랜드명 자체를 중심으로 보여준다.

예:

```text
CaloDetect

음식 사진을 분석하고
식단과 영양 상태를 기록하세요.

[시작하기]
```

또는 추천 기능을 같이 보여줄 경우:

```text
CaloDetect

음식을 기록하고
현재 영양 상태에 맞는 식사를 추천받아보세요.

[음식 분석]
[식사 추천]
```

별도의 과도한 슬로건은 필수가 아니다.

---


# 49. 역할 분담

## A. Backend Core

담당:

- 인증
- Profile / 목표 칼로리
- PostgreSQL Schema
- Meal 저장
- Today Analytics
- Admin 권한
- FastAPI API Schema
- Alembic Migration

### Alembic 규칙

**Alembic Migration은 A 담당자만 생성한다.**

B 또는 C 담당자가 DB Schema 변경이 필요하면 A에게 변경사항을 전달한다.

금지:

```text
여러 담당자가 각자 Codex로 Alembic revision 생성
```

목적:

```text
multiple heads
migration conflict
merge 충돌
배포 DB 불일치
```

방지.

## B. Vision / Data / Recommendation

담당:

- YOLO26m FastAPI 연동
- Food Master 검토
- 추천 후보 데이터
- Recommendation Rule / Engine
- Detection / Correction
- Streamlit QA 화면

## C. Frontend / Integration / Deploy

담당:

- React 전체 화면
- Home
- Meal Scan
- Recommendation
- History
- Profile
- Docker
- Deploy
- Backend API Integration

## 협업 규칙

Week 1 초반에 아래를 우선 확정한다.

```text
FastAPI Endpoint
Request Schema
Response Schema
Error Schema
```

C 담당자는 Backend 구현 완료를 기다리지 않고 Mock JSON으로 Frontend 개발을 병행할 수 있다.

---

# 50. GitHub 규칙

Repository 하나를 Source of Truth로 사용한다.

권장:

```text
main
develop
feature/*
fix/*
```

예:

```text
feature/auth
feature/profile
feature/meal-scan
feature/recommendation
feature/retraining  # P1에서만 사용
```

원칙:

- main 직접 대규모 수정 금지
- 기능 단위 Branch
- 기능 단위 Commit
- 가능하면 PR
- requirements 변경 기록
- DB 변경 시 Migration 포함
- README 실행법 최신 유지

---

# 51. AI Coding 규칙

Codex / Claude / Gemini 등을 사용할 수 있다.

하지만:

1. Repository 구조를 임의 변경하지 않는다.
2. 담당 범위 중심으로 수정한다.
3. 관련 없는 파일까지 대규모 수정하지 않는다.
4. 기존 기능 삭제 전 dependency 확인
5. 변경 전후 git diff 확인
6. 변경 후 테스트
7. 실제 실행 방법과 README 일치
8. TODO/TBD를 임의 결정하지 않는다.

---

# 52. P0 — 반드시 구현

- 이메일 회원가입 / 로그인 / 로그아웃
- 사용자 Profile
- 목표 Calories
- 음식 이미지 업로드
- YOLO26m Detection
- 음식명 사용자 수정
- 섭취량 입력
- 기존 영양정보 조회
- Python 영양 계산
- PostgreSQL 저장
- 사용자별 기록 영구화
- 오늘 상태 분석
- History
- 추천 후보 데이터 검토/구축
- 식사 추천 3개
- Rule 기반 추천 이유
- 추천 다양성
- 최근 음식 반복 Penalty
- Detection Correction 저장
- 모델 개선 활용 동의 확인
- Streamlit QA 승인/거절
- 승인 샘플 누적
- 테스트

# 53. P1 — P0 완료 후

- Google OAuth
- LLM 자연어 설명
- 추천 카드 하단 후속 질문 UI (`왜?`, `다른 메뉴`)
- 자연어 조건 추천
- what-if 식사 시뮬레이션
- 자연어 식단 기록
- 실제 Retraining 실행
- Candidate Model 평가
- Model Registry
- Promote / Rollback
- 운동 추천
- Menu Vision
- 웹캠 촬영

P1은 P0가 끝난 뒤에만 구현한다.

# 54. ROADMAP — 현재 구현 금지

다음 기능은 `ROADMAP.md`에만 기록한다.

이번 MVP에서 구현하지 않는다.

```text
위치 기반 매장 검색
Apple Health
Android Health Connect
Coach Platform
Coach Ranking
Feed
Follow
Like
Calo Point
Challenge
광고
인플루언서 식단
Partnership
장보기 추천
Barcode
기업 Wellness
지자체 건강사업
음식-영양 DB 매핑 규칙 고도화
외부 음식 DB 자동 연동
매핑 테이블 버전 관리
```

---

# 55. 3주 개발 일정

## Week 1 — 기반 확정

```text
Repository 분석
AGENTS.md
IMPLEMENTATION_PLAN.md
DB Schema
Alembic
API Request/Response Schema
이메일 Auth
Profile
추천 후보 데이터 검토
추천 데이터 출처 확정
TBD 핵심 항목 결정
```

### Week 1 종료 조건

```text
회원가입/로그인 가능
Profile 저장 가능
DB Migration 완료
API Schema 확정
Recommendation 조건 파라미터 스키마 확정
추천 후보 데이터 방향 및 출처 확정
```

## Week 2 — 핵심 사용자 Flow

```text
사진 업로드
YOLO26m
사용자 수정
섭취량
영양 계산
Meal 저장
Home 오늘 상태
History
식사 추천 3개
```

### Week 2 종료 조건

한 명의 사용자 계정으로 사진 업로드부터 식사 추천까지 한 바퀴 실제 동작.

## Week 3 — QA / 통합 / 배포

```text
Correction
Streamlit QA
UI 수정
예외처리
통합테스트
Docker
배포
발표 Demo
```

### 마지막 2~3일

**신규 기능 추가 금지.**

오직:

```text
Bug Fix
Integration Test
Deployment Test
Demo Rehearsal
PPT 검증
```

만 수행한다.

# 56. 테스트

## Auth

- 회원가입
- 중복 이메일
- 로그인
- 잘못된 비밀번호
- 로그아웃
- 사용자 데이터 분리

## Profile

- BMR
- TDEE
- minimum
- calorie range
- 5000 상한
- 연령 정책 확정 후 하한 테스트

## Meal

- 이미지 업로드
- 정상 탐지
- 다중 음식
- 사진 1장 → detection_log 여러 행 생성
- detect 응답 → detection_id 배열 반환
- 각 meal_item과 detection_log 연결
- 수동 선택 음식 → detection_log_id null 허용
- 탐지 실패
- 낮은 confidence
- 사용자 수정
- 섭취량
- 영양 계산
- 저장

## Persistence

```text
저장
→ 로그아웃
→ 로그인
→ 기록 유지
```

## Date / Timezone

```text
23:59 KST
00:01 KST
```

날짜 경계 집계 검증.

## Recommendation

- 남은 Calories 반영
- 부족 영양소 반영
- Sugar/Sodium 기준 반영
- meal_type 반영
- 최근 메뉴 반복 Penalty
- 제외 음식
- 3개 다양성
- 사용자 화면에 내부 Score 미노출

## Correction / QA

- `POST /meals/detect` → detection_id 목록 생성
- `POST /meals` 요청의 각 meal_item에 detection_id 포함 (수동 선택은 null)
- corrected_label이 다르면 같은 Transaction에서 detection_log 갱신
- consent false → Retraining Candidate 미생성
- consent true → PENDING 생성
- GET /users/me/consent 조회
- PUT /users/me/consent 변경
- 동의 철회 후 기존 PENDING 샘플 제외
- APPROVED 샘플 재수정 시 기존 행 유지 + 새 PENDING 생성
- approve
- reject
- 일반 사용자 `/admin/*` 호출 → 403
- admin 사용자 `/admin/*` 호출 → 정상 처리
- seed/CLI로 생성한 최초 admin 로그인 성공
- 일반 사용자가 role을 임의 승격할 수 없는지 확인
- Streamlit QA가 Backend Admin API를 통해 동작하는지 확인

## Regression

기존 CaloDetect 기능이 깨지지 않는지 확인한다.

# 57. 로그

최소 로그:

```text
auth
meal save
YOLO inference
detection correction
nutrition lookup failure
recommendation
admin QA approve / reject
consent change
LLM failure          # P1
retraining request   # P1
model promotion      # P1
model rollback       # P1
```

`# P1` 표시 로그는 해당 기능을 P1에서 구현할 때 추가한다. P0에서 미리 만들지 않는다.

민감정보 로그 금지.

---

# 58. API 초안

기존 API가 있으면 우선 재사용한다.

## P0 API

```text
POST   /auth/signup
POST   /auth/login
POST   /auth/logout

GET    /users/me
GET    /users/me/profile
PUT    /users/me/profile
GET    /users/me/consent
PUT    /users/me/consent

POST   /meals/detect
POST   /meals
GET    /meals/today
GET    /meals/history

GET    /analytics/today

POST   /recommendations/meals

POST   /detections/{id}/correction   # 식단 저장 후 Correction 재수정용

GET    /admin/retraining/samples
POST   /admin/retraining/samples/{id}/approve
POST   /admin/retraining/samples/{id}/reject
```

기본 Correction은 `POST /meals` 저장 Transaction 안에서 처리한다.

모든 `/admin/*` Endpoint는 관리자 권한 검사를 수행한다.

```text
role != admin
→ 403 Forbidden
```

Streamlit QA는 DB에 직접 쓰지 않고 위 Admin API를 호출한다.


## P1 API — 현재 구현 금지

```text
POST /admin/retraining/run
GET  /admin/models
POST /admin/models/{id}/promote
POST /admin/models/{id}/rollback
POST /recommendations/exercises
```

향후 대화형 기능은 별도 Chat API부터 만들기보다 기존 Service 함수를 우선 재사용한다.

예:

```text
get_today_status()
recommend_meals(filters)
simulate_meal()
log_meal()
```

P1 Endpoint를 P0 구현으로 오해하지 않도록 코드에 미리 빈 Route를 만들지 않는다.

# 59. 완료 기준

아래 시나리오가 실제 계정에서 끝까지 동작해야 한다.

```text
회원가입
→ 로그인
→ Profile 저장
→ 음식 사진 업로드
→ YOLO26m
→ 음식 확인/수정
→ 섭취량
→ 영양 계산
→ PostgreSQL 저장
→ Home 상태
→ 식사 추천 3개
→ Rule 기반 추천 이유
→ History
→ 로그아웃
→ 재로그인
→ 기록 유지
```

오탐의 경우:

```text
사용자 수정
→ Correction 저장
→ consent 확인
→ Streamlit QA
→ 승인/거절
```

까지 시연 가능해야 한다.

# 60. 최종 산출물

P0 완료 시:

```text
실행 가능한 Source Code
FastAPI Backend
React Frontend
PostgreSQL
Alembic Migration
YOLO26m Integration
Meal Persistence
Nutrition Calculation
Today Analytics
Recommendation Engine
Correction Flow
Streamlit Admin QA
Tests
Dockerfile
.env.example
README.md
Deployment Guide
AGENTS.md
IMPLEMENTATION_PLAN.md
ARCHITECTURE.md
DATA_SCHEMA.md
MODEL_EXPERIMENTS.md
ROADMAP.md
```

# 61. Codex 첫 작업 지시

Codex는 본 문서를 받은 후 전체 기능을 한 번에 구현하지 않는다.

## 1단계

Repository를 분석한다.

## 2단계

아래 표를 작성한다.

```text
기능 | 현재 상태 | REUSE | MODIFY | NEW | 담당 | 우선순위
```

## 3단계

다음 문서를 먼저 생성한다.

```text
AGENTS.md
IMPLEMENTATION_PLAN.md
ARCHITECTURE.md
DATA_SCHEMA.md
MODEL_EXPERIMENTS.md
ROADMAP.md
```

## 4단계

TBD 목록을 별도 표로 정리한다.

## 5단계 — P0 개발 순서

```text
Auth
→ Profile
→ DB
→ API Schema
→ Meal Persistence
→ YOLO Integration
→ Nutrition Calculation
→ Today Analytics
→ Recommendation Data
→ Recommendation Engine
→ React Integration
→ Correction
→ Streamlit QA
```

## 6단계

각 단계마다:

```text
구현
→ 테스트
→ 오류 수정
→ Commit
→ 다음 단계
```

순서로 진행한다.

## Codex가 멈추고 질문해야 하는 상황

- 데이터 출처가 없음
- 영양값이 없음
- 기존 DB 구조와 문서가 충돌
- 인증 방식 확정 필요
- 이미지 저장 정책 필요
- 사용자 개인정보 정책 필요
- 기존 기능 삭제가 필요해 보임
- Dependency 대규모 변경 필요
- P1 기능을 먼저 만들어야만 할 것처럼 보임
- A 담당자가 아닌 작업에서 Alembic Migration 생성이 필요해 보임
- 관리자 권한 정책과 충돌하는 변경이 필요해 보임

# 62. 최종 판단 원칙

기능 추가 여부를 판단할 때 다음을 확인한다.

```text
1. 현재 MVP 사용자 Flow를 완성하는가?
2. 3주 안에 Demo 가능한가?
3. 기존 기능을 재사용할 수 있는가?
4. 식단 기록 또는 식사 추천에 직접 필요한가?
```

현재 핵심 Flow에 직접 필요하지 않다면 P1 또는 ROADMAP으로 이동한다.

---

# 63. 최종 개발 원칙

> **서비스명은 CaloDetect로 통일한다.**

> **CaloDetect 2.0은 내부 개발 버전명으로만 사용한다.**

> **기존 프로젝트를 살린다.**

> **3명·3주 안에 끝까지 돌아가는 사용자 Flow가 우선이다.**

> **P0는 음식 인식 → 기록 → 상태 분석 → 식사 추천 → Correction QA까지다.**

> **실제 재학습, Model Registry, LLM, 운동 추천은 P1이다.**

> **영양 계산은 Python/DB가 하고 LLM은 설명만 한다.**

> **영양성분 기준 데이터 파일은 `CaloDetect_nutrition_all_matched(1).csv`이다.**


> **추천 후보 데이터는 실제 출처가 있는 데이터만 사용한다.**

> **사용자 화면에는 추천 Score 숫자보다 추천 이유를 보여준다.**

> **사용자 이미지를 재학습에 사용할 경우 별도 동의를 확인한다.**

> **사용자 날짜 기준은 Asia/Seoul이다.**

> **마지막 2~3일에는 신규 기능을 추가하지 않는다.**

# 64. Codex에 전달할 최종 명령

> 현재 Repository를 먼저 분석하라. 기존 CaloDetect의 모델, 음식 데이터, `CaloDetect_nutrition_all_matched(1).csv`, 기존 영양정보 조회 구조, Streamlit, 음식 탐지 및 기록 기능을 최대한 보존하라. 전체 프로젝트를 새로 만들지 않는다. 먼저 `AGENTS.md`와 `IMPLEMENTATION_PLAN.md`를 작성하고 REUSE/MODIFY/NEW를 분리한다. 이번 3주 프로젝트의 P0는 회원·프로필·음식 탐지·영양 계산·저장·오늘 상태·식사 추천 3개·History·Correction·Streamlit QA까지다. 실제 재학습, Model Registry, LLM, 운동 추천은 P1로 둔다. 팀에서 결정하지 않은 항목은 `TBD`로 남기고 임의로 채우지 않는다.
추천 API는 현재 P0 기능만 구현하되, 향후 자연어 조건이나 챗봇이 동일 엔진을 재사용할 수 있도록 요청 스키마와 Service 계층을 UI와 분리한다. 각 기능은 구현 후 테스트를 통과한 다음 다음 단계로 진행한다. 이후 기준 변경은 `CHANGELOG.md`에 남기고 Master Spec 본문에는 현재 기준만 유지한다.
