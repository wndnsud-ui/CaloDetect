# CaloDetect — Codex 커뮤니티 기능 업무지시서 (v11 보충, 수정본 v5)
> 내부 프로젝트 버전: CaloDetect 2.0
> 기준일: 2026-10-15 (사용자 승인일 2026-10-14)
> 상위 문서: `docs/rules/CaloDetect_Codex_통합_업무지시서_20261002_v11.md` (Master Spec, 원문 수정 금지)
> 용도: 커뮤니티(식단 공유·좋아요/추천·포인트·주간 랭킹) 개발 작업 지시
> 변경 이력: `CHANGELOG.md` 참고

**v4 → v5 변경 요약 (최신)**
- **공통 잠금 규칙** 추가: 반응 추가·취소·게시물 삭제 모두 게시물 행을 먼저 잠근다(반응은 FOR SHARE, 삭제는 FOR UPDATE). 잠금 순서는 게시물 → 반응, 상태 확인·SUM 계산은 잠금 이후(§6-0, §6-1).
  - 막는 문제: 반응 추가와 삭제가 겹치면 작성자가 포인트를 지키는 문제, 반응 취소와 삭제가 겹치면 작성자가 이중 감점되는 문제.
- 반응 취소 순서 변경: 1단계가 게시물 잠금(이전: 반응 잠금)(§6-0).
- 포인트 원장 **DB 부분 unique 제약** 2개 추가, 위반 시 rollback 후 404(§5-4).
- FK에 CASCADE 금지, 식단 삭제·회원 탈퇴 경로 확인(§0 C8, §5-1), DB 격리 수준 확인(§0 C9).
- 미리보기 값은 **예상액**, 최종값은 DELETE 응답의 `deducted`(§9).
- 반응 후 원본 식단 수정 시 반응·포인트 유지 명시, 삭제 게시물의 사진 사본은 이번 범위에서 물리 삭제하지 않음 명시(§3, §6-1).
- 순서를 강제한 PostgreSQL 동시성 테스트 추가(§13 #28~#31).

**v3 → v4 변경 요약**
- **공유 시점 스냅샷 삭제.** 게시물은 원본 식단을 실시간으로 반영한다. 공유 후 원본 식단이 수정되면 게시물도 바뀐다(§2, §5-1-1, §9). `snapshot`·`snapshot_version` 컬럼 제거.
- **게시물 삭제 시 작성자가 받은 포인트를 감점**한다. 반응한 회원의 포인트는 유지한다. 삭제 전 경고 확인창을 띄운다(§2, §6-1, §9, §11-1).
- 사진 사본은 위치정보 보호용으로 유지(식단 내용 고정 목적 아님)(§5-2).
- 아래 v1~v3 변경 요약 중 "스냅샷"·"삭제 시 포인트 유지" 관련 내용은 v4로 대체되었다.

**v1 → v2 변경 요약**
- (v4에서 폐기) 공유 시점 스냅샷 저장.
- 반응 취소를 **감점**으로 명시하고, 취소 전 **경고 확인창**을 띄운다. 감점은 발생한 주의 점수에 반영한다(§6, §10, §11-1).
- 응답에서 내부 회원 ID 제거, **`is_me`**로 대체(§9, §10).
- 공개 사진은 **메타데이터(EXIF·GPS)를 제거한 사본**만 제공(§8).
- 동시 취소 이중 회수 방지(§6), 피드 커서를 `(created_at, id)`로 변경(§9).
- 착수 전 확인 항목 추가: 실제 Alembic head, DELETE의 CSRF 적용, 사진 환경 검사 범위, 팀 승인·migration 담당(§0).
- 다계정 담합 한계를 TBD에 명시(§3).

**v2 → v3 변경 요약**
- **공유 가능한 식단 API** `GET /community/eligible-meals` 추가(§9, §11-2).
- 사진 사본 생성 후 **DB 커밋이 실패해도 사본 파일을 정리**(§5-2).
- 반응 취소 트랜잭션의 **처리 순서를 단계별로 명시**(§6).
- 삭제한 게시물의 식단 **재공유 금지 이유와 409 안내 문구** 명시(§5-1, §7).
- 반응 취소 경고창을 여는 동안 **버튼 연타 방지**(§11-1).
- 주간 랭킹 펼침을 **`closed / hovered / pinned` 상태 머신**으로 구현, 타이머 정리 규칙 추가(§11-3).
- 구현 시 하지 말 것 명시: SQLite 방언 분기로 잠금 우회, CORS 미들웨어 설정 전체 교체(§4, §6, §9).

---

# 0. 착수 전 확인

구현 전에 아래를 확인해 결과와 근거(파일·줄 번호)를 보고한다. "차단"에 해당하면 그 항목에 의존하는 작업만 멈추고 보고한다.

| ID | 확인 대상 | 전제 | 다를 때 |
|---|---|---|---|
| C1 | `AGENTS.md`·`docs/rules/README.md`·`DEVELOPMENT_RULES.md`·`PENDING_DECISIONS.md`의 migration 담당·신규 기능 조항 | §1의 사용자 승인이 팀 합의로 기록되어 있고, migration 작성 주체가 정해져 있음 | 승인 기록이나 migration 담당 합의가 없으면 migration·모델 작업 **차단** 후 보고 |
| C2 | Alembic 실제 head의 **revision 문자열**(파일명이 아님) | 단일 head | 실제 값으로 `down_revision`을 맞춘다. 복수 head면 임의 병합하지 말고 **차단** |
| C3 | 다른 브랜치의 진행 중 migration(예: 섭취량 수정 `consumption_ratio`) | 없음 | 있으면 병합 순서를 보고하고, 나중 병합하는 쪽이 rebase해 head를 하나로 유지 |
| C4 | 기존 CSRF·출처 검사가 **DELETE 메서드**에도 적용되는가 | 적용됨 | 적용되지 않으면 DELETE 라우트를 열기 전에 보고. CSRF 없이 DELETE를 허용하지 않는다 |
| C5 | `require_image_environment`가 검사하는 조건(저장 설정만 / loopback·개발 환경 포함) | 저장 설정만 검사 | loopback·개발 환경까지 검사하면 다른 회원이 공개 사진을 볼 수 없음 → 사진 공개 기능 **제한** 보고(기존 검사는 바꾸지 않는다) |
| C6 | `MealItem`에 `consumption_ratio`(섭취 비율) 컬럼 존재 여부 | 없음 | 있으면 게시물 조회 시 섭취량을 유효 배율(`serving_multiplier × consumption_ratio`)로 표시(§5-1-1) |
| C7 | 사진 처리 라이브러리(Pillow 등) 사용 가능 여부 | 기존 업로드 검증에 사용 중 | 없으면 보고(의존성 추가는 승인 후) |
| C8 | 기존 코드의 **식단 삭제 경로**(API·관리자·스크립트)와 **회원 탈퇴 경로**, 그리고 `meals`·`users`를 참조하는 기존 FK의 ondelete 설정 | 식단 삭제·회원 탈퇴 경로 없음 | 경로가 있으면 공유된 식단·회원을 지울 때 FK 오류가 날 수 있음 → 기존 경로는 수정하지 말고 보고, 처리 방식 TBD(§3). CASCADE로 우회하지 않는다 |
| C9 | PostgreSQL **트랜잭션 격리 수준**(엔진·세션 설정) | READ COMMITTED(기본값) | REPEATABLE READ 이상이면 §6-0의 "잠금 이후 문장은 최신 커밋을 본다" 전제가 깨진다(대기 후 직렬화 오류) → 보고 후 커뮤니티 쓰기 작업 **차단** |

---

# 1. 문서 목적

본 문서는 기존 CaloDetect 식단 기록 데이터를 기반으로 **회원 간 소셜 기능**을 추가하기 위한 보충 업무지시서다.

```text
식단 기록
→ 커뮤니티에 식단 공유 (게시물은 원본 식단을 실시간 반영)
→ 다른 회원이 좋아요 / 추천
→ 작성자·반응한 회원에게 포인트 적립 (반응 취소 시 양쪽 감점, 게시물 삭제 시 작성자 감점)
→ 주간 랭킹
```

Master Spec §54(ROADMAP — 현재 구현 금지)의 `Feed`, `Like`, `Calo Point`는 **2026-10-14 사용자 승인**으로 현재 범위에 포함한다.
Master Spec 원문은 수정하지 않고, 승인 내용은 `CHANGELOG.md`, `docs/rules/PENDING_DECISIONS.md`, `docs/planning/ROADMAP.md`에 기록한다.

다음 항목은 여전히 구현하지 않는다.

```text
Follow
Coach Platform / Coach Ranking
Challenge
광고 / Partnership / 인플루언서 식단
포인트 사용처(교환·혜택·결제)
댓글
```

---

# 2. 사용자 확정 사항 (2026-10-14)

| 항목 | 결정 |
|---|---|
| 공개 범위 | 음식명 + 영양 + 코멘트 + **사진** 공개 가능 |
| 공개 내용의 기준 시점 | **원본 식단 실시간 반영.** 공유 후 원본 식단이 수정되면 게시물도 바뀐다(공유 시점 스냅샷 없음) |
| 포인트 지급 대상 | **게시물 작성자 + 반응을 누른 회원 모두** |
| 어뷰징 방지 | **본인 글 반응 금지**, **게시물당 1인 1회(좋아요·추천 각각) + 취소 시 감점** |
| 반응 취소 | **감점**으로 처리하고(작성자·반응자 모두), 취소 전 **경고 확인창**을 띄운다. 감점은 취소한 주의 점수에 반영한다 |
| 게시물 삭제 | **작성자가 그 게시물로 받은 포인트만 감점**한다. 반응한 회원이 받은 포인트는 유지한다. 삭제 전 **경고 확인창**을 띄우고, 감점은 삭제한 주의 점수에 반영한다 |
| 회원 식별 노출 | 응답에 내부 회원 ID를 넣지 않고 **`is_me`**만 제공 |
| 포인트 표시 범위 | 잔액·적립/감점 내역 + **주간 랭킹** |
| 화면 형태 | 사용자 제공 소셜 앱 예시(담벼락) 기준 피드형 UI |

---

# 3. 미확정 항목 — TBD 유지

임의로 확정하지 않는다. 개발 기본값은 설정값으로만 두고 운영 확정값처럼 표시하지 않는다.

| 항목 | 개발 처리 |
|---|---|
| 포인트 수치 | 개발 기본값 받은 좋아요 1 / 받은 추천 3 / 누른 반응 1, 환경변수로 조정 |
| 사진 공개 동의 문구 | 게시물별 명시 체크(기본 해제)만 적용, 정식 문구 TBD |
| 포인트 사용처·소멸 기한 | 미구현, 응답에 `points_usage: null` |
| 반응 후 원본 식단 수정 | **현재 허용.** 게시물이 원본을 실시간 반영하므로 반응을 받은 뒤 내용이 바뀔 수 있고, **기존 반응·포인트는 그대로 유지**한다. "수정됨" 표시·변경 이력·수정 범위 제한은 향후 검토(TBD) |
| 공유된 식단·회원 삭제 시 처리 | 현재 식단 삭제·회원 탈퇴 경로 없음(§0 C8로 확인). 경로가 생기면 게시물 삭제(§6-1 감점)를 먼저 거치는 방식 검토, TBD |
| 원본 사진 변경 시 사본 갱신 | 현재 기능상 식단 사진은 바뀌지 않음. 교체·추가 기능이 생기면 규칙 TBD |
| 신고·관리자 숨김 | 미구현, TBD |
| 표시 이름 | 기존 회원 `name` 사용. 닉네임 도입 여부 TBD |
| 일일 적립 상한·추천 횟수 제한 | 미적용(사용자 선택에서 제외) |
| **다계정 담합** | **현재 규칙으로는 막지 못함.** 계정 두 개로 서로 반응하면 게시물마다 포인트가 쌓이고, 직접 선택 식단으로 게시물을 계속 만들 수 있어 랭킹 조작이 가능하다. 대응(공유 횟수 제한·가입 검증 등) TBD |
| 공개 사진 사본 보관 기간 | 게시물 삭제 시 `community_post_images` 행과 사본 파일은 **이번 범위에서 물리 삭제하지 않는다.** 삭제된 게시물의 공개 사진 경로는 404로 차단한다. 실제 삭제·보관 기간은 이미지 보관 정책 확정 후 처리(삭제 시 commit 이후에 실행) |

---

# 4. 절대 금지 사항

```text
Master Spec 원문 수정 금지
기존 테이블 컬럼 변경·삭제 금지 (새 테이블만 추가)
기존 식단·탐지·사진 API의 동작 변경 금지
기존 소유자 전용 사진 경로(/meals/images/{id})를 공개로 바꾸지 말 것
원본 사진 파일을 공개 경로로 직접 제공 금지 (메타데이터 제거 사본만)
이메일·내부 식별 이메일·내부 회원 ID·탐지 ID·신뢰도를 커뮤니티 응답에 노출 금지
클라이언트가 보낸 영양값·포인트 수치를 신뢰 금지 (서버 저장값·서버 설정만 사용)
포인트 잔액을 별도 컬럼으로 덮어쓰기 금지 (원장 합계로만 계산)
CSRF 검사 없이 DELETE 라우트 허용 금지
CORS 미들웨어 설정 전체 교체 금지 (기존 allow_methods에 DELETE만 추가)
DB 방언(SQLite/PostgreSQL) 분기로 잠금·동시성 규칙을 다르게 구현하는 것 금지
본 문서 범위 밖 기능(댓글, Follow, 포인트 사용처)의 빈 Route·빈 파일 선생성 금지
```

---

# 4-1. 음식 표시 원칙 — 기존 한식 150종 기준

CaloDetect 모델(best.pt)과 영양 CSV(`CaloDetect_nutrition_all_matched.csv`)는 **한식 완성 요리 150종**(`class_id` 0~149) 단위다.
샐러드·요거트 같은 개별 제품이나 재료, 브랜드 상품을 하나하나 인식·나열하지 못한다. 커뮤니티는 이 한계를 그대로 따른다.

```text
게시물의 음식 = 원본 식단의 현재 meal_items (class_id → food_name)
음식 단위   = 완성 요리 1개 (예: 된장찌개, 잡곡밥, 제육볶음, 배추김치)
재료 분해·제품명·브랜드·자유 입력 음식명 표시 금지
새 음식 매핑·외부 음식 DB·LLM 음식명 추정 금지 (Master Spec §17, §54 유지)
150종에 없는 음식은 공유 화면에서 추가할 수 없다 (기록 단계의 직접 선택도 기존 카탈로그만 사용)
코멘트(자유 텍스트)에 음식 이야기를 쓰는 것은 허용 — 단, 영양 계산·태그에는 쓰지 않는다
```

## 표시 이름

| 원본 food_name | 화면 표시 |
|---|---|
| `곰탕_설렁탕` | 곰탕/설렁탕 |
| `떡국_만두국` | 떡국/만두국 |
| 그 외 | 원본 그대로 |

`_`만 `/`로 바꾸고 DB·API 값은 원본을 유지한다(프런트 표시 함수 1곳에서 처리).

## 한 상 요약 — 밥·국·반찬 구성

한식 식단은 반찬 수가 많아 음식명을 전부 나열하면 길어진다. 피드에서는 기존 CSV `category`로 **한 상 요약**을 만든다.

| 묶음 | CSV category |
|---|---|
| 반찬 | `반찬류`, `김치류`, `생채·무침류`, `채소/나물`, `안주/반찬` |
| 주메뉴 | 그 외 전부 (밥류, 국/탕/찌개, 국 및 탕류, 면류, 육류, 생선류, 해산물, 찜류, 분식류, 보양식 등) |

```text
요약 규칙
1. 주메뉴를 저장 순서대로 최대 3개 표시
2. 주메뉴가 4개 이상이면 "외 n개"
3. 반찬은 이름 대신 "반찬 n가지"로 묶음
4. 주메뉴 없이 반찬만 있으면 반찬 이름을 최대 3개 표시 + "외 n개"

예) 잡곡밥 · 된장찌개 · 제육볶음 + 반찬 3가지
예) 비빔밥 + 반찬 1가지
예) 삼계탕
```

게시물을 누르거나 "구성 보기"를 펼치면 전체 음식 목록을 보여준다. 이때 섭취량은 배율 숫자가 아니라 CSV `unit` 기준으로 표시한다.

```text
된장찌개  그릇 (약 400ml) × 1
잡곡밥    공기 (약 210g) × 1
배추김치  1회 (약 100g) × 0.5
```

category 묶음 규칙은 화면 표시용이며 추천 엔진의 category 사용(Master Spec §22~24)과 별개다. 묶음 목록은 서비스 상수 1곳에 두고 CSV를 수정하지 않는다.

---

# 5. 데이터 모델

Alembic revision 1개를 추가한다. `down_revision`은 **§0 C2로 확인한 실제 head revision 문자열**로 지정한다(예상값 `20261002_02_p0` 또는 `20261002_02`, 반드시 확인).

## 5-1. community_posts

| 컬럼 | 타입 | 규칙 |
|---|---|---|
| id | String(36) PK | UUID |
| user_id | FK users.id, index, **ondelete 지정 안 함(기본 NO ACTION/RESTRICT)** | 작성자 |
| meal_id | FK meals.id, **unique**, **ondelete 지정 안 함(CASCADE 금지)** | 같은 식단은 한 번만 공유(**삭제 글 포함**, 부분 인덱스 사용 금지). 게시물 내용을 조회하는 기준 |
| comment | String(300) | 앞뒤 공백 제거 |
| show_photo | Boolean | 기본 False. True일 때만 사진 공개 |
| created_at | DateTime(tz), index | UTC |
| deleted_at | DateTime(tz), nullable | 작성자 삭제 시각(소프트 삭제) |

인덱스: `(created_at DESC, id DESC)` — 피드 커서용.

게시물 테이블에는 식단 내용(음식·영양·배율)을 **복사해 저장하지 않는다.** 게시물의 식단 내용은 조회할 때마다 `meal_id`로 원본 식단을 읽어 만든다(§5-1-1).

**FK에 CASCADE를 쓰지 않는 이유:** 원본 식단이나 회원이 지워질 때 게시물이 DB에서 자동 삭제되면 §6-1의 작성자 감점이 실행되지 않고, 원장 행(`post_id` FK)도 함께 깨진다. 기존 식단 삭제·회원 탈퇴 경로는 §0 C8로 확인하고, 이번 범위에서 그 경로를 수정하지 않는다. 그런 경로가 있으면 "공유된 식단·회원 삭제 시 처리"를 보고하고 TBD로 남긴다(§3).

**삭제 후 재공유를 막는 이유:** 게시물을 삭제하면 작성자가 받은 포인트는 감점되지만, 반응한 회원이 받은 포인트는 유지된다(§6-1). 삭제 후 같은 식단을 다시 공유할 수 있으면 "공유 → 반응 받기 → 삭제 → 재공유 → 다시 반응"을 반복해 반응한 회원이 포인트를 계속 쌓을 수 있다. 따라서 `meal_id` unique는 삭제 글을 포함해 전체에 적용한다. 재공유 시도는 409와 함께 아래 안내를 반환한다.

```text
활성 게시물이 있는 식단:  "이미 커뮤니티에 공유한 식단이에요."
삭제한 게시물의 식단:     "삭제한 게시물의 식단은 다시 공유할 수 없어요."
```

### 5-1-1. 게시물 식단 내용 — 원본 식단 실시간 반영

게시물을 조회할 때 서버가 `meal_id`의 **현재** `meals`·`meal_items`와 `foods`를 읽어 아래 구조를 만든다. 공유 후 원본 식단의 음식·섭취량·영양값이 수정되면 다음 조회부터 게시물에도 그대로 반영된다.

```json
{
  "meal_date": "2026-10-14",
  "meal_type": "lunch",
  "items": [
    {"class_id": 0, "food_name": "곰탕_설렁탕", "category": "국/탕/찌개",
     "unit": "그릇 (약 600ml)", "serving_multiplier": 1.0,
     "nutrition": {"cal": 0, "carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "sodium": 0}}
  ],
  "totals": {"cal": 0, "carbs": 0, "protein": 0, "fat": 0, "sugar": 0, "sodium": 0}
}
```

구성 규칙:

```text
items는 현재 meal_items의 저장 순서 그대로, nutrition은 meal_items에 저장된 서버 값 그대로
food_name·category·unit은 foods 테이블(기존 CSV 시드)에서 조회한 값
serving_multiplier는 표시용 섭취 배율: C6에서 consumption_ratio가 있으면 serving_multiplier × consumption_ratio, 없으면 serving_multiplier
totals는 items의 nutrition 합계(소수 2자리)
이메일·탐지 ID·신뢰도·사진 경로는 넣지 않는다
식단 내용을 community_posts에 복사·캐시하지 않는다
```

- 피드는 게시물 여러 개를 한 번에 조회하므로, `meal_items`·`foods`를 게시물마다 따로 조회하지 말고 **페이지 단위로 한 번에 조회**(IN 조건 또는 eager load)해 N+1 쿼리를 피한다.
- 원본 식단의 항목이 0개가 되면(현재 기능상 발생하지 않음) `items: []`, totals 0으로 반환하고 피드에서 숨기지 않는다.
- 반응을 받은 뒤 내용이 바뀌었다는 표시("수정됨")는 이번 범위에서 만들지 않는다(§3 TBD).

## 5-2. community_post_images

공개할 사진의 **메타데이터를 제거한 사본**을 가리킨다. 사본은 위치정보 보호를 위한 것이며 식단 내용 고정 목적이 아니다.

- 현재 구조에서는 한 식단에 연결된 사진(탐지 이미지)이 공유 후 바뀌지 않으므로, 공유할 때 만든 사본을 계속 사용한다.
- 원본 사진이 교체·추가·삭제되는 기능이 생기면 사본 갱신 규칙을 따로 정한다(§3 TBD). 그 전까지 원본 경로를 공개 경로로 대신 제공하지 않는다.

| 컬럼 | 타입 | 규칙 |
|---|---|---|
| id | String(36) PK | UUID. 공개 경로의 `image_id` |
| post_id | FK community_posts.id, index | |
| source_image_id | String(36) | 원본 이미지 ID(내부 추적용, 응답 비노출) |
| storage_key | String | 서버가 생성한 사본 파일 키. 원본 파일명 사용 금지 |
| position | Integer | 표시 순서 |
| created_at | DateTime(tz) | |

- `show_photo=true`로 공유할 때만 행과 사본을 만든다.
- 사본 생성: 원본을 열어 방향 정보만 픽셀에 반영(`ImageOps.exif_transpose` 등)한 뒤 **EXIF·GPS·XMP·ICC 외 메타데이터를 모두 제거**하고 같은 형식(JPG/PNG)으로 다시 저장한다. 저장 위치는 기존 `IMAGE_STORAGE_DIR` 아래 커뮤니티 전용 하위 폴더.
- 사본 생성이 실패하면 공유 전체를 실패시킨다(사진 없이 조용히 공유하지 않음). 이미 쓴 사본 파일은 정리한다.
- **사본은 만들어졌지만 DB 커밋이 실패한 경우에도** 이번 요청에서 만든 사본 파일을 모두 삭제한다. 공유 처리 전체를 아래 형태로 감싼다.

  ```python
  created_files = []
  try:
      for src in source_images:
          created_files.append(save_sanitized_copy(src, community_dir))  # 서버 생성 파일명
      # 게시물·이미지 행 추가
      db.commit()
  except Exception:
      db.rollback()
      for path in created_files:
          path.unlink(missing_ok=True)   # 이번 요청에서 만든 사본만 삭제
      raise
  ```

  기존 원본 사진 파일과 다른 게시물의 사본은 절대 삭제하지 않는다.
- `UNIQUE(post_id, position)`.

## 5-3. community_reactions

| 컬럼 | 타입 | 규칙 |
|---|---|---|
| id | String(36) PK | UUID |
| post_id | FK community_posts.id, index | |
| user_id | FK users.id, index | 반응한 회원 |
| kind | String(16) | CHECK `kind IN ('like','recommend')` |
| created_at | DateTime(tz) | |

제약: `UNIQUE(post_id, user_id, kind)` — 동시 요청도 DB에서 1건만 허용.

## 5-4. point_transactions (포인트 원장)

| 컬럼 | 타입 | 규칙 |
|---|---|---|
| id | String(36) PK | UUID |
| user_id | FK users.id, index | 포인트 소유자 |
| amount | Integer | 적립 +, 감점 − |
| reason | String(32) | 아래 코드 |
| post_id | FK community_posts.id, nullable, index | |
| reaction_id | String(36), nullable, index | FK 없음(반응 행은 취소 시 삭제됨) |
| created_at | DateTime(tz), index | 주간 집계 기준 |

reason 코드:

```text
적립: like_received / recommend_received / like_given / recommend_given
반응 취소 감점: 위 4개 + "_revoked"
게시물 삭제 감점: post_deleted_revoked (작성자 1행, reaction_id 없음)
```

DB 중복 방어 (애플리케이션 확인과 별개로 DB에서도 막는다):

```python
# 반응 관련 행: 한 반응에 같은 사유의 행은 1개만 (지급 2행 + 감점 2행)
Index("uq_point_tx_reaction_reason", "reaction_id", "reason", unique=True,
      postgresql_where=text("reaction_id IS NOT NULL"),
      sqlite_where=text("reaction_id IS NOT NULL"))
# 게시물 삭제 감점: 게시물당 1개만
Index("uq_point_tx_post_deleted", "post_id", unique=True,
      postgresql_where=text("reason = 'post_deleted_revoked'"),
      sqlite_where=text("reason = 'post_deleted_revoked'"))
```

- `(reaction_id, user_id, reason)`이 아니라 `(reaction_id, reason)`으로 충분하다. 본인 글 반응이 금지되어 작성자와 반응자가 같은 반응에서 같은 사유를 가질 수 없다.
- `reaction_id`가 NULL인 행(게시물 삭제 감점)은 첫 번째 인덱스로 막히지 않으므로(PostgreSQL은 NULL끼리 중복으로 보지 않음) 두 번째 부분 인덱스로 따로 막는다.
- 이 제약에 걸려 commit이 실패하면 rollback 후 404(이미 처리됨)로 응답한다. 500으로 내보내지 않는다.

---

# 6. 포인트 규칙

| 이벤트 | 작성자 | 누른 회원 |
|---|---|---|
| 좋아요 추가 | +`COMMUNITY_LIKE_RECEIVED_POINTS` (기본 1) | +`COMMUNITY_REACTION_GIVEN_POINTS` (기본 1) |
| 추천 추가 | +`COMMUNITY_RECOMMEND_RECEIVED_POINTS` (기본 3) | +`COMMUNITY_REACTION_GIVEN_POINTS` (기본 1) |
| 반응 취소 (**감점**) | 해당 반응으로 **실제 지급된 금액**만큼 − | 동일 |

필수 규칙:

```text
잔액 = SUM(point_transactions.amount)
취소 시 원 지급 행을 수정·삭제하지 않고 음수(감점) 행을 추가한다
감점 금액은 현재 설정값이 아니라 reaction_id로 찾은 원 지급액 기준이다
설정값이 0이면 원장 행을 만들지 않는다
반응 추가 + 포인트 지급은 한 트랜잭션, 반응 취소 + 감점도 한 트랜잭션
누르기/취소를 반복해도 순증가가 0이어야 한다
```

## 6-0. 공통 잠금 규칙 (반응 추가·반응 취소·게시물 삭제)

세 작업은 모두 같은 게시물의 포인트를 바꾼다. 서로 다른 행만 잠그면 동시에 실행될 때 정합성이 깨진다.

```text
[깨지는 예 1] 반응 추가 + 게시물 삭제
  추가가 커밋 전에 삭제가 SUM을 계산 → 추가분(+3)이 감점되지 않은 채 삭제 완료
  → 삭제된 게시물에 반응이 남고 작성자가 +3을 계속 가짐 (취소도 404라 회수 불가)

[깨지는 예 2] 반응 취소 + 게시물 삭제
  취소의 −3이 커밋 전에 삭제가 SUM을 계산 → 원 지급 +3을 다시 감점
  → 같은 3점이 작성자에게서 두 번 빠짐
```

따라서 아래 규칙을 **모든 커뮤니티 상태 변경**에 공통 적용한다.

```text
1. 항상 community_posts 행을 먼저 잠근다
     반응 추가·반응 취소: FOR SHARE   (SQLAlchemy: with_for_update(read=True))
     게시물 삭제:         FOR UPDATE  (SQLAlchemy: with_for_update())
   → 반응끼리는 서로 막지 않고, 삭제와 반응은 반드시 차례로 실행된다
2. 잠금 순서는 항상 게시물 → 반응. 이 순서를 바꾸지 않는다(교착 상태 방지)
3. deleted_at 확인, 본인 글 확인, 포인트 SUM 계산은 반드시 잠금을 얻은 "다음" 문장에서 한다
   (PostgreSQL READ COMMITTED에서는 잠금을 기다린 뒤 실행되는 문장이 상대가 커밋한 결과를 본다. §0 C9)
4. 잠금 이전에 읽은 값(게시물 상태·작성자·포인트)으로 판단하지 않는다
5. 한 요청 = 한 트랜잭션. 중간 commit 금지
6. DB 방언 분기를 만들지 않는다. with_for_update()는 SQLite에서 SQLAlchemy가 자동으로 무시한다
   (기존 탐지 처리도 같은 방식). 실제 동시성 판정은 PostgreSQL 테스트(§13 #14, #25, #28, #29)로 한다
```

### 반응 추가 트랜잭션

```text
1. community_posts 행을 FOR SHARE로 잠근다 → 없거나 deleted_at이 있으면 404
2. 작성자 == 요청자이면 403
3. 반응 INSERT (UNIQUE(post_id, user_id, kind) 위반 시 rollback 후 409)
4. 설정값이 0이 아닌 쪽만 지급 행 추가 (작성자 *_received, 반응자 *_given, reaction_id = 새 반응 id)
5. commit
```

### 반응 취소 트랜잭션

```text
1. community_posts 행을 FOR SHARE로 잠근다 → 없거나 deleted_at이 있으면 404
2. (post_id, user_id, kind)로 반응 행을 FOR UPDATE로 잠근다 → 없으면 404
3. DELETE ... WHERE id = :reaction_id 로 삭제하고 삭제된 행 수를 확인한다 → 정확히 1이 아니면 rollback 후 404
4. point_transactions에서 reaction_id = :reaction_id 이고 amount > 0 인 원 지급 행을 조회한다
   (작성자 *_received 1건, 반응자 *_given 1건. 설정값 0이었던 쪽은 행이 없을 수 있다)
5. 같은 reaction_id에 *_revoked 행이 이미 있으면 감점을 추가하지 않는다 (방어적 확인)
6. 원 지급 행마다 user_id·post_id·reaction_id를 그대로, amount = -원 지급액,
   reason = 원 reason + "_revoked" 로 감점 행을 추가한다
7. commit. 응답의 deducted는 6에서 추가한 금액으로 만든다
   (commit 중 §5-4 부분 unique 위반이 나면 rollback 후 404 — 다른 요청이 이미 처리함)
```

```python
post = (db.query(CommunityPost)
          .filter(CommunityPost.id == post_id)
          .with_for_update(read=True)          # 1. 게시물 먼저 (FOR SHARE)
          .first())
if post is None or post.deleted_at is not None:
    raise NotFound
reaction = (db.query(CommunityReaction)
              .filter_by(post_id=post_id, user_id=user.id, kind=kind)
              .with_for_update()               # 2. 그다음 반응 (FOR UPDATE)
              .first())
if reaction is None:
    raise NotFound
deleted = (db.query(CommunityReaction)
             .filter(CommunityReaction.id == reaction.id)
             .delete(synchronize_session=False))
if deleted != 1:
    db.rollback()
    raise NotFound
already = db.query(PointTransaction).filter(
    PointTransaction.reaction_id == reaction.id,
    PointTransaction.reason.endswith("_revoked", autoescape=True)).first()  # '_'를 LIKE 와일드카드로 해석하지 않게
added = []
if already is None:
    originals = db.query(PointTransaction).filter(
        PointTransaction.reaction_id == reaction.id,
        PointTransaction.amount > 0).all()
    for tx in originals:
        row = PointTransaction(user_id=tx.user_id, amount=-tx.amount,
                               reason=f"{tx.reason}_revoked",
                               post_id=tx.post_id, reaction_id=reaction.id)
        db.add(row)
        added.append(row)
try:
    db.commit()
except IntegrityError:
    db.rollback()
    raise NotFound
```

- 원장의 `reaction_id`는 FK가 없으므로 반응 행을 삭제한 뒤에도 원 지급 행을 찾을 수 있다.
- ORM `db.delete(obj)`만 쓰고 삭제 행 수 확인을 생략하지 않는다.

설정(`backend/app/config.py`, 범위 0~100):

```text
COMMUNITY_LIKE_RECEIVED_POINTS=1
COMMUNITY_RECOMMEND_RECEIVED_POINTS=3
COMMUNITY_REACTION_GIVEN_POINTS=1
COMMUNITY_RANKING_SIZE=10
```

## 6-1. 게시물 삭제 시 감점 (작성자만)

| 대상 | 처리 |
|---|---|
| 작성자 | 그 게시물로 받은 **순 포인트**(받은 좋아요·추천 적립 − 이미 감점된 반응 취소분)만큼 감점 |
| 반응한 회원 | **감점하지 않는다.** `*_given` 적립은 유지 |

삭제 트랜잭션 순서 (§6-0 공통 잠금 규칙 적용):

```text
1. community_posts 행을 FOR UPDATE로 잠근다 (with_for_update())
   → 진행 중인 반응 추가·취소(FOR SHARE)가 모두 commit/rollback될 때까지 기다린다
   → 잠금을 얻은 뒤에 확인: 없으면 404, 작성자가 아니면 403, 이미 deleted_at이 있으면 404
2. 잠금을 얻은 뒤의 새 문장으로 작성자의 이 게시물 순 받은 포인트를 계산한다
   (기다리는 동안 커밋된 반응 추가 +n·반응 취소 −n이 모두 반영된 값)
   net = SUM(amount) WHERE user_id = 작성자 AND post_id = :post_id
         AND reason IN ('like_received','recommend_received',
                        'like_received_revoked','recommend_received_revoked')
3. 같은 post_id에 post_deleted_revoked 행이 이미 있으면 감점하지 않는다 (방어적 확인)
4. net > 0 이면 감점 행 1개 추가:
   user_id = 작성자, amount = -net, reason = 'post_deleted_revoked', post_id = :post_id, reaction_id = NULL
5. UPDATE community_posts SET deleted_at = now WHERE id = :post_id AND deleted_at IS NULL
   → 갱신된 행 수가 정확히 1이 아니면 rollback 후 404
6. 한 번에 commit. 응답의 deducted는 4에서 추가한 금액(없으면 0)
   (commit 중 §5-4 부분 unique 위반이 나면 rollback 후 404 — 다른 요청이 이미 처리함)
7. commit 이후의 후처리(로그, 이후 사본 파일 삭제 정책이 생길 경우의 파일 삭제)는 트랜잭션 밖에서 한다
```

```python
RECEIVED_REASONS = ("like_received", "recommend_received",
                    "like_received_revoked", "recommend_received_revoked")

post = (db.query(CommunityPost)
          .filter(CommunityPost.id == post_id)
          .with_for_update()                    # FOR UPDATE: 반응 추가·취소와 직렬화
          .first())
if post is None or post.deleted_at is not None:
    raise NotFound
if post.user_id != user.id:
    raise Forbidden
net = db.query(func.coalesce(func.sum(PointTransaction.amount), 0)).filter(
    PointTransaction.user_id == post.user_id,
    PointTransaction.post_id == post.id,
    PointTransaction.reason.in_(RECEIVED_REASONS)).scalar()   # 잠금 이후 실행
exists = db.query(PointTransaction.id).filter(
    PointTransaction.post_id == post.id,
    PointTransaction.reason == "post_deleted_revoked").first()
deducted = 0
if net > 0 and exists is None:
    db.add(PointTransaction(user_id=post.user_id, amount=-net,
                            reason="post_deleted_revoked", post_id=post.id))
    deducted = -net
updated = (db.query(CommunityPost)
             .filter(CommunityPost.id == post.id, CommunityPost.deleted_at.is_(None))
             .update({"deleted_at": utcnow()}, synchronize_session=False))
if updated != 1:
    db.rollback()
    raise NotFound
try:
    db.commit()
except IntegrityError:
    db.rollback()
    raise NotFound
```

- 반응 행은 삭제하지 않고 남긴다. 삭제된 게시물에는 반응 추가·취소가 모두 404이므로, 이후 반응 취소로 인한 추가 감점은 생기지 않는다.
- 반응한 회원의 `*_given` 행과 이미 기록된 반응 취소 감점 행은 건드리지 않는다.
- 감점은 **삭제한 시각이 속한 주**의 점수에 반영한다(§10). 이번 주 합계가 0 이하가 되면 랭킹 목록에서 빠진다.
- 동시 삭제 요청은 1번 잠금과 5번 갱신 행 수 확인으로 한 건만 처리된다. DB 방언 분기를 만들지 않는다.
- 공유 사진 사본 파일과 `community_post_images` 행은 이번 범위에서 **삭제하지 않는다**(§3). 공개 사진 경로는 삭제된 게시물에 404를 반환하므로 노출되지 않는다.
- 나중에 사본 파일을 지우기로 하면, 파일 삭제는 반드시 **commit이 성공한 뒤** 트랜잭션 밖에서 한다. 트랜잭션 안에서 지웠다가 rollback되면 게시물은 살아 있는데 사진 파일만 사라진다.

---

# 7. 어뷰징 방지

| 규칙 | 처리 |
|---|---|
| 본인 글 반응 | 403 |
| 같은 종류 중복 반응 | 409 (사전 조회 + DB unique 위반 시 rollback 후 409) |
| 없는 반응 취소 | 404 |
| 동시 취소 | 한 건만 감점, 나머지 404 |
| 삭제된 게시물에 반응 추가·취소 | 404 |
| 게시물 삭제 | 작성자 받은 순 포인트만 감점(§6-1), 반응한 회원 포인트 유지 |
| 동시 삭제·이미 삭제된 게시물 삭제 | 한 건만 처리, 나머지 404, 감점 1회 |
| 반복 누르기/취소 | 감점 규칙으로 순증가 0 |
| 타인 식단 공유 | 404 (존재 여부를 드러내지 않음) |
| 이미 공유했거나 삭제한 게시물의 식단 재공유 | 409 + §5-1 안내 문구 |

다계정 담합은 현재 규칙으로 막지 못한다(§3 TBD).

---

# 8. 사진 공개 규칙

```text
공유 시 show_photo=true를 명시한 경우에만 공개
사진 없는 식단에 show_photo=true → 422
공유할 때 식단 사진의 메타데이터 제거 사본을 만들어 community_post_images에 연결한다(§5-2)
공개 경로: GET /community/posts/{post_id}/images/{image_id}
```

공개 경로는 다음을 **모두** 확인한다.

```text
게시물 존재 + 삭제되지 않음
show_photo == true
image_id가 해당 게시물의 community_post_images 행
사본 파일이 존재
기존 require_image_environment 검사 유지 (C5 결과에 따라 제한 보고)
응답 헤더 Cache-Control: private, no-store
```

- 공개 경로는 **사본만** 제공한다. 원본 파일 경로로 대체 제공하지 않는다.
- 공개 게시물 경로에 다른 사진 ID를 넣어 우회 조회할 수 없어야 한다.
- 기존 `/meals/images/{id}`는 계속 소유자 전용이다.
- 현재 기능상 식단 사진은 공유 후 바뀌지 않으므로 공유할 때 만든 사본을 계속 쓴다. 원본 사진 변경 기능이 생기면 사본 갱신 규칙을 따로 정한다(§3 TBD).

---

# 9. API

모든 경로는 로그인 필수(`CurrentUser`). 변경 요청은 기존 쿠키 CSRF·출처 검사를 그대로 적용한다(**DELETE 포함, §0 C4**).
CORS는 기존 미들웨어 설정의 `allow_methods`에 `DELETE`만 추가한다. `allow_origins`·`allow_headers` 등 다른 설정은 바꾸지 않고, 미들웨어 등록을 새로 쓰지 않는다. (기존 POST가 `X-CSRF-Token` 헤더로 동작하므로 헤더 설정은 이미 충족된 것으로 보고, 다르면 §0에서 보고한다. 인증은 쿠키 기반이라 `Authorization` 헤더를 추가하지 않는다. `OPTIONS` 프리플라이트는 미들웨어가 처리한다.)

| Method | Path | 설명 |
|---|---|---|
| GET | `/community/posts?limit=20&cursor=&mine=false` | 최신순 피드. limit 1~50, `cursor`는 이전 응답의 `next_cursor` |
| GET | `/community/eligible-meals?limit=20` | 공유 작성 화면용. 내 최근 식단 중 **공유 이력이 없는** 식단 목록(쓰기 없음) |
| POST | `/community/posts` | `{meal_id, comment, show_photo}` 본인 식단 공유(사진 공개 시 사본 생성) → 201 |
| GET | `/community/posts/{id}/delete-preview` | 작성자만. 삭제 시 감점 예정액 조회(쓰기 없음, 경고창용). 타인 403 |
| DELETE | `/community/posts/{id}` | 작성자만 소프트 삭제 + 작성자 받은 포인트 감점(§6-1) → `{"deleted": true, "deducted": {"me": -n}}`. 타인 403 |
| POST | `/community/posts/{id}/reactions/{like\|recommend}` | 반응 추가 + 포인트 지급 → 201, 갱신된 게시물 |
| DELETE | `/community/posts/{id}/reactions/{like\|recommend}` | 반응 취소 + 감점 → 갱신된 게시물 + `deducted` |
| GET | `/community/posts/{id}/reactions/{like\|recommend}/revoke-preview` | 취소 시 감점 예정액 조회(쓰기 없음, 경고창용) |
| GET | `/community/posts/{id}/images/{image_id}` | 공개 선택 게시물 사진(메타데이터 제거 사본) |
| GET | `/community/points/me` | 잔액·이번 주 획득·이번 주 감점·지급 기준·최근 내역 30건 |
| GET | `/community/ranking/weekly` | 주간 랭킹 + 내 순위 |

게시물 응답:

```json
{
  "id": "uuid",
  "created_at": "ISO8601+00:00",
  "author": {"name": "...", "is_me": false},
  "is_mine": false,
  "comment": "...",
  "show_photo": true,
  "meal_id": null,
  "meal": { "...": "원본 식단의 현재 내용(§5-1-1 구조)" },
  "image_urls": ["/api/community/posts/{id}/images/{image_id}"],
  "counts": {"like": 0, "recommend": 0},
  "my_reactions": ["like"]
}
```

피드 응답: `{"items": [게시물...], "next_cursor": "...|null"}`

```text
author에는 내부 회원 ID를 넣지 않는다. 본인 여부는 author.is_me(= is_mine)로만 판단한다
meal은 조회 시점에 원본 meals·meal_items·foods로 만든다(§5-1-1). 페이지 단위로 한 번에 조회해 N+1을 피한다
meal_id는 본인 게시물에만 채운다 (공유 여부 판단용)
image_urls는 show_photo=false면 빈 배열
클라이언트가 보낸 음식명·영양값은 사용하지 않는다
한 상 요약 문자열은 서버가 만들지 않는다 — 프런트가 §4-1 규칙으로 표시한다
```

커서 규칙:

```text
정렬: created_at DESC, id DESC
next_cursor: limit만큼 반환됐을 때만 마지막 게시물의 (created_at, id)를 인코딩한 불투명 문자열(예: base64url), 아니면 null
다음 페이지 조건: (created_at, id) < (cursor.created_at, cursor.id)
잘못된 cursor는 422
프런트는 cursor를 URLSearchParams로 그대로 전달한다
```

eligible-meals 규칙:

```text
본인 식단만 조회. meal_date desc, 같은 날짜는 식사 생성 시각 desc
community_posts에 같은 meal_id 행이 하나라도 있으면(삭제 글 포함) 제외
limit 1~50, 기본 20. 이번 범위에서는 페이지네이션 없이 최근 limit개만 반환
항목 0개 식단은 제외
기존 /meals API는 수정하지 않는다
```

응답:

```json
{
  "items": [
    {"meal_id": "uuid", "meal_date": "2026-10-14", "meal_type": "lunch", "has_photo": true,
     "items": [{"class_id": 0, "food_name": "곰탕_설렁탕", "category": "국/탕/찌개"}]}
  ]
}
```

`items`는 §4-1 한 상 요약을 만드는 데 필요한 값만 담는다(영양값·배율·탐지 ID·사진 경로 제외). `has_photo`는 공유 화면의 사진 공개 체크박스 활성 여부에 쓴다.

반응 취소 응답의 `deducted`: `{"me": -1, "author": -3}`처럼 이번 취소로 실제 감점된 금액(작성자 금액은 표시용 숫자만, 작성자 신원 정보 없음).

revoke-preview 응답: `{"me": -1, "author": -3, "counts_in_week": "current"}` — 원 지급액 기준 감점 예정액. 반응이 없으면 404.

delete-preview 응답: `{"me": -12, "reactors_affected": false}` — §6-1의 순 받은 포인트 기준 작성자 감점 예정액(없으면 0). 반응한 회원은 감점되지 않음을 화면이 안내할 수 있게 `reactors_affected`는 항상 false. 이미 삭제된 게시물은 404.

**미리보기는 예상액이다:**

```text
revoke-preview·delete-preview 값은 조회 시점의 예상액이며 잠금을 걸지 않는다
미리보기와 실제 DELETE 사이에 다른 회원의 반응 추가·취소가 있으면 실제 감점액이 달라질 수 있다
실제 감점액은 DELETE 트랜잭션 안에서 잠금 이후 다시 계산하며, DELETE 응답의 deducted가 최종값이다
프런트는 완료 토스트·포인트 표시에 반드시 응답의 deducted를 쓰고, 미리보기 값을 재사용하지 않는다
```

---

# 10. 주간 랭킹

```text
집계 시작: 한국 시간(Asia/Seoul) 이번 주 월요일 00:00 → UTC 변환 후 비교
집계 값: 해당 기간 point_transactions.amount 합계 (적립 + 감점)
감점은 취소·삭제한 시각이 속한 주에 반영한다 — 지난주 반응을 이번 주에 취소하거나, 지난주에 반응을 받은 게시물을 이번 주에 삭제하면 이번 주 점수에서 감점
표시 대상: 합계 > 0 인 회원
정렬: 포인트 desc, 내부 user_id asc (정렬에만 사용, 응답 비노출)
동점: 같은 순위 (1, 1, 3)
상위 COMMUNITY_RANKING_SIZE명 + 내 순위(me)를 별도 반환
지난주 적립은 이번 주 랭킹에서 제외되지만 잔액에는 남는다
```

응답:

```json
{
  "timezone": "Asia/Seoul",
  "week_start": "2026-10-12T00:00:00+09:00",
  "items": [{"rank": 1, "name": "...", "points": 0, "is_me": false}],
  "me": {"rank": 5, "points": 0, "deducted_this_week": 0}
}
```

`items`에 내부 회원 ID를 넣지 않는다. 내 이번 주 합계가 0 이하이면 `me.rank`는 null.

---

# 11. 사용자 화면

사이드바에 **커뮤니티** 메뉴를 `히스토리`와 `마이페이지` 사이에 추가한다. 비회원은 로그인 화면으로 보낸다.
`entry.jsx`의 sessionStorage 허용 화면 목록에도 추가한다.

## 11-1. 피드 (담벼락형)

사용자 제공 예시 기준:

```text
상단: "커뮤니티" 제목 / [전체] [내 게시물] 알약 탭 (선택 탭은 짙은 배경)
게시물: 왼쪽 원형 아바타(이름 첫 글자) | 오른쪽 본문
  이름(굵게) + 상대 시간(방금 전 / n분 전 / n시간 전 / n일 전 / 7일 이후 날짜) + 끼니 태그
  코멘트 — 4줄 초과 시 말줄임 + "더보기 / 접기"
  한 상 요약 (§4-1) — 예: "잡곡밥 · 된장찌개 · 제육볶음 + 반찬 3가지"  [구성 보기]
  "745 kcal  탄 88.3g  단 53.2g  지 19.5g" 한 줄 (원본 식단의 현재 totals)
  사진(공개 선택 시) — 본문 폭, 둥근 모서리
  ♡ 좋아요 수   ☆ 추천 수   (본인 글이면 비활성 + 오른쪽 "삭제")
게시물 사이: 카드 대신 구분선
하단: "더 보기" 페이지네이션 (next_cursor)
```

React 목록 key는 게시물 `id`를 쓴다(회원 ID 없음).

반응 버튼:

```text
테두리 없는 아이콘 + 숫자
좋아요 활성: 채운 하트, 빨강 계열
추천 활성: 채운 별, 노랑 계열
aria-pressed, aria-label("좋아요 n개") 제공
반응 후 게시물 숫자 + 포인트 + 랭킹을 다시 조회
```

**반응 취소 경고 (감점 확인창):**

```text
이미 누른 반응 버튼을 다시 누르면 바로 취소하지 않고 경고 확인창을 띄운다
열기 전에 revoke-preview로 감점 예정액을 조회한다
조회 중에는 해당 버튼을 disabled + aria-busy로 두어 연타로 요청·확인창이 중복되지 않게 한다
확인창이 열려 있는 동안 같은 게시물의 반응 버튼은 비활성화한다
"감점하고 취소"도 DELETE 요청 중에는 disabled로 두어 중복 전송을 막는다

[경고 아이콘] 반응을 취소하면 포인트가 감점돼요
  내 포인트 −1 P
  작성자 포인트 −3 P
  지난주에 누른 반응도 이번 주 점수에서 감점돼요.
  [취소하지 않기]  [감점하고 취소]   ← 기본 포커스는 "취소하지 않기"

"감점하고 취소"는 경고 색(빨강 계열)으로 표시
role="alertdialog", aria-labelledby·aria-describedby 제공, Esc = 취소하지 않기
확인 후 DELETE 요청 → 응답의 deducted로 "−1 P 감점됐어요" 토스트 표시
revoke-preview가 404면 확인창 없이 게시물을 다시 조회한다
```

**게시물 삭제 경고 (작성자 감점 확인창):**

```text
본인 글의 "삭제"를 누르면 바로 삭제하지 않고 경고 확인창을 띄운다
열기 전에 delete-preview로 감점 예정액을 조회한다 (조회 중 "삭제" 버튼 disabled + aria-busy)

[경고 아이콘] 게시물을 삭제하면 받은 포인트가 감점돼요
  내 포인트 −12 P   (이 게시물로 받은 좋아요·추천 포인트)
  반응한 회원의 포인트는 그대로 유지돼요.
  삭제한 게시물의 식단은 다시 공유할 수 없어요.
  지난주에 받은 포인트도 이번 주 점수에서 감점돼요.
  [삭제하지 않기]  [감점하고 삭제]   ← 기본 포커스는 "삭제하지 않기"

감점 예정액이 0이면 감점 줄 대신 "이 게시물로 받은 포인트가 없어요."를 표시
"감점하고 삭제"는 경고 색(빨강 계열), DELETE 요청 중 disabled
role="alertdialog", aria-labelledby·aria-describedby 제공, Esc = 삭제하지 않기
확인 후 DELETE 요청 → 응답의 deducted로 "게시물을 삭제했어요 · −12 P 감점" 토스트, 피드·포인트·랭킹 재조회
delete-preview가 404면 확인창 없이 피드를 다시 조회한다
```

## 11-2. 공유 작성

```text
오른쪽 아래 고정 원형 + 버튼 (브랜드 초록, 예시의 보라색 사용 안 함)
PC: 가운데 모달 / 모바일(≤700px): 하단 시트
공유할 식단 선택: GET /community/eligible-meals 결과만 표시 (아직 공유하지 않은 식단)
  사진 공개 체크박스 활성 여부는 has_photo로 판단
  선택지 표기: "10/14 점심 · 잡곡밥 · 된장찌개 + 반찬 3가지" (§4-1 요약 재사용)
  공유 화면에서 음식 추가·수정 불가 — 수정은 기존 히스토리/보정 흐름에서만
코멘트 textarea 최대 300자 + 글자 수 표시
"식단 사진을 다른 회원에게 공개합니다" 체크박스 — 기본 해제, 사진 없는 식단은 비활성
공개 안내: "이름, 식단 날짜·구분, 음식과 영양 정보가 로그인한 회원에게 보입니다.
          사진은 체크한 경우에만 공개되며, 위치 등 사진 정보는 지운 뒤 공개됩니다.
          공유한 뒤 식단을 수정하면 게시물에도 바로 반영됩니다."
공유할 식단이 없으면 "식단 기록하러 가기" 버튼
Esc / 바깥 클릭으로 닫기
```

## 11-3. 포인트 · 랭킹 — 랭킹은 접었다 펼치는 방식

사용자 시안(2026-10-14) 기준. 내 포인트는 항상 보이고, **주간 랭킹은 평소 한 줄로 접혀 있다가 마우스를 올리면 펼쳐진다.**
피드 폭을 넓게 쓰고, 랭킹은 궁금할 때만 보게 하는 것이 목적이다.

### PC (>1050px, 마우스 사용 환경)

오른쪽 열 구성:

```text
[내 포인트 카드]  항상 표시
  잔액(크게) / 이번 주 +n P · 감점 −n P / 지급 기준 4줄 / 최근 내역(접기)
  최근 내역에서 감점(*_revoked) 행은 "감점" 라벨 + 빨강 계열 숫자
  (post_deleted_revoked는 "게시물 삭제로 감점", 반응 취소 감점은 "반응 취소로 감점")

[주간 랭킹 바]    평소 접힌 상태 — 한 줄
  🏆 주간 랭킹   내 순위 5위 · 1,280 P   ▾
```

펼침 동작:

| 동작 | 결과 |
|---|---|
| 랭킹 바에 마우스 올림 | 150ms 후 펼침 (스치기만 할 때 깜빡임 방지) |
| 펼친 패널 밖으로 마우스 이동 | 300ms 후 접힘 (패널로 옮겨 가는 동안 닫히지 않게) |
| 랭킹 바 클릭 | **고정 펼침**(▾ → 📌). 마우스가 나가도 유지, 다시 클릭하면 해제 |
| 키보드 Tab으로 포커스 | 펼침 (`:focus-within`), 포커스가 나가면 접힘 |
| Esc | 접힘 + 고정 해제 |

구현 방식 — 상태 머신과 타이머 정리:

```text
상태는 boolean 대신 'closed' | 'hovered' | 'pinned' 세 값으로 관리한다
타이머는 useRef 하나에 보관하고, 새 타이머를 걸기 전과 상태가 바뀔 때마다 clearTimeout 한다
pinned 상태에서는 mouseenter/mouseleave 타이머를 걸지 않는다
클릭: pinned → closed, 그 외 → pinned (대기 중 타이머는 즉시 정리)
Esc: 타이머 정리 + closed
키보드 포커스(focus-within)는 별도 boolean으로 두고, 화면 표시는 (상태 ≠ closed) || 포커스 중 으로 계산한다
컴포넌트 언마운트 시 useEffect 정리 함수에서 clearTimeout 한다
```

```javascript
const [openState, setOpenState] = useState('closed'); // 'closed' | 'hovered' | 'pinned'
const [focusWithin, setFocusWithin] = useState(false);
const timerRef = useRef(null);
const clearTimer = () => { clearTimeout(timerRef.current); timerRef.current = null; };

useEffect(() => clearTimer, []);  // 언마운트 시 정리

const onMouseEnter = () => {
  if (openState === 'pinned') return;
  clearTimer();
  timerRef.current = setTimeout(() => setOpenState('hovered'), 150);
};
const onMouseLeave = () => {
  if (openState === 'pinned') return;
  clearTimer();
  timerRef.current = setTimeout(() => setOpenState('closed'), 300);
};
const onClick = () => {
  clearTimer();
  setOpenState(prev => (prev === 'pinned' ? 'closed' : 'pinned'));
};
const onKeyDown = (e) => {
  if (e.key === 'Escape') { clearTimer(); setOpenState('closed'); }
};
const isOpen = openState !== 'closed' || focusWithin;
```

hover 타이머 핸들러는 `(hover: hover) and (pointer: fine)` 환경에서만 연결한다.

펼친 패널 내용 (시안 ⑤ 축약판):

```text
[이번 주] [전체 기간]  ← 전체 기간 탭은 TBD, 이번 범위에서는 표시하지 않음
1 🥇 지민   2,350 P
2 🥈 서연   1,980 P
3 🥉 민재   1,680 P
4    혜진   1,420 P
5    혜영·나 1,280 P   ← is_me 행 강조
… 상위 COMMUNITY_RANKING_SIZE명까지, 패널 최대 높이 넘으면 내부 스크롤
내가 목록 밖이면 맨 아래 "내 순위 n위 · n P" 고정 행
"10월 12일(월)부터 집계 · 취소 감점 포함" 안내
```

목록 key는 `rank`와 순서 인덱스를 조합해 쓴다(회원 ID 없음).

표시 방식:

```text
펼친 패널은 랭킹 바 아래로 높이가 늘어나는 아코디언 (레이아웃 밀림 허용)
  → 오른쪽 열이 sticky이므로 피드 위를 덮는 팝오버보다 아코디언이 안전
열고 닫기 애니메이션 200ms 이하, prefers-reduced-motion이면 애니메이션 없음
펼쳐질 때 /community/ranking/weekly 응답이 30초 이상 지났으면 다시 조회
```

### 태블릿·모바일 (≤1050px 또는 hover 미지원 기기)

터치 기기에는 hover가 없으므로 hover 동작을 쓰지 않는다. `@media (hover: hover) and (pointer: fine)`일 때만 hover 펼침을 적용한다.

```text
제목 옆 요약 칩: "1,280 P · 이번 주 5위"
칩 탭 → 하단 시트로 주간 랭킹 표시 (시안 ⑤), 닫기 ×·바깥 탭·아래로 쓸어내리기
내 포인트 상세는 칩의 포인트 부분 탭 → 하단 시트 (시안 ④)
피드 아래에 포인트·랭킹 카드를 반복 배치하지 않는다
```

### 접근성

```text
랭킹 바는 <button aria-expanded aria-controls="ranking-panel">
고정 상태는 aria-pressed로 함께 표시
펼침 상태 변화는 화면 읽기 프로그램에 "주간 랭킹 펼침/접힘"으로 전달
hover만으로 열 수 있는 기능을 두지 않는다 (클릭·키보드로 동일하게 가능)
```

### 이번 범위에서 제외 (시안에 있으나 미구현)

```text
"전체 기간" 랭킹 탭 — 집계 기준 TBD
"이번 달 +n P" — 월간 집계 API 없음, TBD
피드 탭의 "팔로잉" — Follow는 Master Spec §54 구현 금지 유지
게시물 북마크 — 범위 밖
```

포인트 사용처 안내는 표시하지 않는다 (TBD).

화면 검증: 1400px·390px에서 가로 스크롤 없음, + 버튼이 마지막 게시물을 가리지 않도록 하단 여백 확보, PC에서 랭킹 hover 펼침·클릭 고정·Esc 접힘, 터치 환경에서 칩 탭 → 하단 시트, 반응 취소 시 경고창 표시.

---

# 12. 파일 구성

| 구분 | 파일 |
|---|---|
| NEW | `backend/app/community.py` (라우터) |
| NEW | `backend/app/services/community.py` (원본 식단 기반 피드 직렬화·원장·삭제 감점·랭킹 계산) |
| NEW | `backend/app/services/community_images.py` (메타데이터 제거 사본 생성) |
| NEW | `backend/migrations/versions/20261014_01_community.py` |
| NEW | `backend/tests/test_community.py` |
| NEW | `frontend/src/Community.jsx`, `frontend/src/community.css` |
| MODIFY | `backend/app/models.py` (4개 모델 추가만) |
| MODIFY | `backend/app/schemas.py` (`CommunityPostRequest` 추가) |
| MODIFY | `backend/app/config.py` (포인트 설정 4개) |
| MODIFY | `backend/app/main.py` (라우터 등록, CORS DELETE, `/system/status` 항목) |
| MODIFY | `frontend/src/main.jsx`, `entry.jsx`, `Visuals.jsx`(메뉴 아이콘) |
| DOC | `README.md`, `CHANGELOG.md`, `PENDING_DECISIONS.md`, `ROADMAP.md` |

`/system/status`:

```text
available += community_feed, community_points
policy_tbd += community_photo_consent_text, community_point_values, community_point_usage,
              community_multi_account_abuse, community_photo_copy_retention
```

---

# 13. 테스트

`backend/tests/test_community.py` — 회원마다 별도 TestClient(세션 쿠키 분리), SQLite 기본·`RUN_POSTGRES_TESTS=1` 시 PostgreSQL.

| # | 검사 |
|---|---|
| 1 | 본인 식단 공유 성공, 코멘트 공백 제거, 영양 합계 = 저장값, 같은 식단 재공유 409, 타인 식단 404 |
| 2 | 피드에 이메일·탐지 ID·**내부 회원 ID 없음**(`author`에 `id` 키 없음), 타인 글 `meal_id` null, `author.is_me` 정확, `mine=true` 필터 |
| 3 | 본인 글 반응 403, 중복 409, 좋아요+추천 후 잔액(작성자 4 / 누른 회원 2) |
| 4 | 취소 시 감점, 없는 반응 취소 404, 누르기/취소 3회 반복 후 잔액 불변, `_revoked` 원장 행 존재, 응답 `deducted` 값 정확 |
| 5 | 설정 변경 후 취소해도 원 지급액만큼 감점, revoke-preview 값 = 실제 감점액, revoke-preview는 쓰기 없음 |
| 6 | 게시물 삭제: 타인 403, 피드 제외, 반응 추가·취소 404, **작성자 순 받은 포인트만큼 `post_deleted_revoked` 1행 감점**(예: 좋아요+추천 받은 뒤 삭제 → 작성자 −4), **반응한 회원 잔액 불변**, 응답 `deducted` 정확 |
| 7 | 주간 랭킹 동점(1,1,3), 내 순위, 지난주 적립 제외·잔액 유지, **지난주 반응을 이번 주에 취소하면 이번 주 점수에서 감점**, 랭킹 `items`에 회원 ID 없음 |
| 8 | `week_start` — 수요일 01:00 KST·일요일 23:30 KST 모두 같은 주 월요일 00:00 KST |
| 9 | 사진: 비공개 404, 공개 200, 공개 경로에 다른 사진 ID 404, 소유자 경로 타인 404, 사진 없는 식단 공개 요청 422, **공개 응답 이미지에 EXIF·GPS 없음**(GPS 포함 테스트 이미지로 확인), 사본 생성 실패 시 공유 실패·게시물 미생성 |
| 10 | 비로그인 401, CSRF 헤더 없으면 403 — **POST와 DELETE(게시물 삭제·반응 취소) 모두** |
| 11 | 게시물 meal.items의 food_name·category·unit이 foods 카탈로그 값과 일치, 요청에 음식명 필드를 넣으면 422(extra forbid), `community_posts`에 식단 내용 컬럼 없음 |
| 12 | **원본 실시간 반영**: 공유 후 원본 meal_items의 nutrition·배율·음식을 바꾸면(직접 DB 갱신으로 모의) 다음 피드 조회의 meal·totals에 바로 반영. 사진 사본은 그대로 |
| 13 | **커서**: 같은 `created_at`을 가진 게시물 여러 개가 페이지 경계에 걸려도 누락·중복 없음, 잘못된 cursor 422 |
| 14 | **동시 취소**(PostgreSQL): 같은 반응에 DELETE 2건 동시 → 한 건 성공·한 건 404, 감점 행 1개. SQLite에서는 미검증 표기 |
| 15 | (C6에서 `consumption_ratio`가 있을 때만) 게시물 meal.items의 `serving_multiplier` = 기준 배율 × 섭취 비율, 섭취 비율을 바꾸면 게시물에도 반영 |
| 16 | (프런트 단위 테스트 또는 수동 확인) 한 상 요약: 주메뉴 3개+외 n개, 반찬 묶음, 반찬만 있는 식단, `_` → `/` 표시 |
| 17 | (수동 확인) 랭킹: 마우스 올림 150ms 후 펼침, 벗어나면 300ms 후 접힘, 클릭 고정·재클릭 해제, Tab 포커스로 펼침, Esc 접힘, 터치 기기에서 hover 미적용·칩 탭 시 하단 시트 |
| 18 | (수동 확인) 반응 취소 경고창: 감점 예정액 표시, 기본 포커스 "취소하지 않기", Esc로 닫으면 반응 유지, 확인 시 감점 토스트, **버튼 연타 시 요청·확인창 1회만** |
| 19 | **eligible-meals**: 본인 식단만, 활성·삭제 게시물의 식단 모두 제외, 항목 0개 식단 제외, `has_photo` 정확, 영양값·탐지 ID·사진 경로 미포함, 타인 식단 미포함 |
| 20 | **재공유 409 문구**: 활성 게시물의 식단 → "이미 커뮤니티에 공유한 식단이에요.", 삭제한 게시물의 식단 → "삭제한 게시물의 식단은 다시 공유할 수 없어요." |
| 21 | **커밋 실패 시 사본 정리**: 사진 공개 공유에서 commit 실패를 주입(monkeypatch) → 게시물·이미지 행 없음, 이번 요청에서 만든 사본 파일 없음, 원본 사진 파일은 그대로 |
| 22 | **취소 순서**: 설정값 0이었던 쪽(원 지급 행 없음)은 감점 행도 생기지 않음, 이미 `_revoked` 행이 있는 reaction_id에는 감점이 추가되지 않음 |
| 23 | (수동 확인) 랭킹 상태 머신: hover로 펼친 뒤 클릭하면 고정, 고정 상태에서 마우스가 나가도 유지, 펼침 대기 중 클릭해도 깜빡이지 않음, 화면 이동(언마운트) 후 콘솔 경고 없음 |
| 24 | **삭제 감점 계산**: 좋아요 받음 → 그 좋아요가 취소됨(작성자 −1 이미 감점) → 추천 받음 → 게시물 삭제 시 작성자 감점액 = 순 받은 포인트(3)만. 받은 포인트가 0이면 감점 행 없음. delete-preview 값 = 실제 감점액, delete-preview는 쓰기 없음, 타인 403 |
| 25 | **삭제 감점 1회**: 같은 게시물 DELETE 2회 → 두 번째 404, `post_deleted_revoked` 행 1개. PostgreSQL에서 동시 삭제 2건 → 한 건 성공·한 건 404(SQLite는 미검증 표기) |
| 26 | **주간 반영**: 지난주에 반응을 받은 게시물을 이번 주에 삭제하면 이번 주 점수에서 감점, 지난주 집계는 변하지 않음 |
| 27 | (수동 확인) 게시물 삭제 경고창: 감점 예정액·"반응한 회원의 포인트는 그대로" 안내 표시, 기본 포커스 "삭제하지 않기", Esc로 닫으면 게시물 유지, 받은 포인트 0이면 대체 문구, 확인 시 감점 토스트(응답 `deducted` 값 사용) |
| 28 | **(PostgreSQL, 순서 강제) 반응 추가 + 게시물 삭제**: 세션 A가 게시물 FOR SHARE → 추천 INSERT·지급(커밋 전) / 세션 B가 삭제 시작 → **B가 대기하는지 확인** → A commit → B 완료. 결과: 작성자 감점액에 A의 +3 포함, 작성자 순증가 0, 반대 순서(B 삭제 먼저 commit → A 시작)면 A는 404이고 반응·지급 행 없음 |
| 29 | **(PostgreSQL, 순서 강제) 반응 취소 + 게시물 삭제**: 세션 A가 취소 진행(−3 감점 행 추가, 커밋 전) / 세션 B가 삭제 시작 → B 대기 확인 → A commit → B 완료. 결과: B의 감점액에 이미 취소된 3이 포함되지 않음, **작성자 이중 감점 없음**(작성자 원장 합계 = 이 게시물 관련 0). 반대 순서면 A는 404 |
| 30 | **원장 부분 unique**: 같은 reaction_id·reason 행을 직접 2개 넣으면 IntegrityError, 같은 post_id에 `post_deleted_revoked` 2개도 IntegrityError, `reaction_id`가 NULL인 다른 사유 행은 제약에 걸리지 않음. API 경로에서 이 제약이 걸리면 500이 아니라 404 |
| 31 | **잠금 순서**: (코드 검토 또는 PostgreSQL 테스트) 반응 추가·취소·삭제 모두 첫 쿼리가 `community_posts` 잠금이며, 반응 행 잠금은 그 뒤에만 나온다. 반응 2건 동시 추가(서로 다른 회원)는 서로 대기하지 않는다 |

순서 강제 테스트 작성 방법(#28·#29):

```text
TestClient 대신 서비스 함수를 PostgreSQL 세션 2개로 직접 호출한다
세션 A는 commit 직전에서 멈추도록 단계를 나누어 호출한다(또는 commit을 늦추는 훅 주입)
세션 B는 별도 스레드에서 실행하고, 일정 시간(예: 0.5초) 안에 끝나지 않으면 "대기 중"으로 판정한다
그 뒤 A를 commit하고 B 스레드 종료를 기다려 결과를 검증한다
타이밍에 기대는 단순 동시 실행(두 요청을 동시에 던지기)만으로 판정하지 않는다
SQLite에서는 미검증으로 표기한다
```

기존 전체 테스트가 회귀 없이 통과해야 한다.

---

# 14. 로그

```text
community post created
community post deleted (deducted 금액 포함, 회원 정보 제외)
community reaction {like|recommend}
community reaction {like|recommend} revoked
community image sanitize failed
```

이메일·이름·코멘트 원문·사진 경로·회원 ID는 로그에 남기지 않는다.

---

# 15. 완료 기준

```text
§0 확인 결과 보고(C1~C9), 차단 항목 없음
alembic upgrade head 성공(실제 head에 연결, 단일 head 유지), downgrade 시 새 테이블만 제거
backend 전체 pytest 통과 (test_community 포함)
frontend npm run build 성공
한식 식단 예시(잡곡밥+된장찌개+제육볶음+반찬 3종, 비빔밥 단품, 반찬만 있는 식단)로 한 상 요약 확인
로컬에서 회원 2명으로 공유 → 좋아요/추천 → 포인트·랭킹 변화 → 취소 경고창 → 감점 확인
공유 후 원본 식단을 수정하면 게시물에도 반영됨 확인
게시물 삭제 경고창 → 작성자만 감점, 반응한 회원 포인트 유지 확인
공유 작성 화면에 아직 공유하지 않은 식단만 나오고, 삭제한 게시물의 식단을 재공유하면 안내 문구가 나옴 확인
사진 공개/비공개 게시물 각각 확인, 공개 사진 다운로드 파일에 위치정보 없음 확인
1400px / 390px 화면 확인
CHANGELOG에 사용자 승인일(2026-10-14)·범위·검증 결과 기록
PostgreSQL에서 순서 강제 동시성 테스트(#14, #25, #28, #29) 통과, 미실행 시 "미검증" 표기
PENDING_DECISIONS에 §3 TBD 표 추가 (다계정 담합·사진 사본 보관·반응 후 원본 수정·공유된 식단/회원 삭제 처리 포함)
```

---

# 16. Codex에 전달할 명령

> `AGENTS.md`와 `docs/rules/README.md` 순서대로 규칙을 읽은 뒤, 본 보충 업무지시서(`CaloDetect_Codex_커뮤니티_업무지시서_20261015_v5.md`)에 따라 커뮤니티 기능을 구현하라. 먼저 §0의 C1~C9를 확인해 근거(파일·줄 번호)와 함께 보고하고, 차단 항목이 있으면 그 항목에 의존하는 작업은 멈춰라. Master Spec §54의 Feed/Like/Calo Point는 2026-10-14 사용자 승인으로 현재 범위에 포함되며, 원문은 수정하지 않는다. 기존 테이블·API·사진 권한은 변경하지 않고 새 테이블 4개와 `/community` 라우터만 추가한다. migration의 `down_revision`은 실제 head revision 문자열로 지정하라. 게시물은 식단 내용을 복사하지 않고 조회할 때마다 원본 식단을 읽어 보여준다(공유 후 원본이 수정되면 게시물도 바뀐다). 공개 사진은 메타데이터를 제거한 사본으로만 제공한다. 게시물 삭제 시에는 §6-1 순서로 작성자가 그 게시물로 받은 순 포인트만 감점하고 반응한 회원의 포인트는 유지하며, 삭제 전 감점 예정액을 보여주는 경고 확인창을 띄워라. 포인트는 원장 합계로만 계산하라. 반응 추가·반응 취소·게시물 삭제는 §6-0 공통 잠금 규칙에 따라 항상 게시물 행을 먼저 잠그고(반응은 FOR SHARE, 삭제는 FOR UPDATE), 잠금 순서는 게시물 → 반응으로 고정하며, 삭제 여부 확인과 포인트 합계 계산은 잠금 이후에 하라. 원장에는 §5-4의 부분 unique 제약 2개를 두고, 위반 시 rollback 후 404로 응답하라. FK에는 CASCADE를 쓰지 마라. 미리보기 값은 예상액이며 화면에는 DELETE 응답의 deducted를 최종값으로 표시하라. DB 방언 분기는 만들지 마라. 사진 사본은 DB 커밋이 실패해도 이번 요청에서 만든 파일을 정리하라. 공유 작성 화면은 `GET /community/eligible-meals`로 아직 공유하지 않은 식단만 보여주고, 삭제한 게시물의 식단은 재공유할 수 없게 하라(meal_id에는 부분 인덱스 금지). CORS는 기존 설정에 DELETE만 추가하고 미들웨어를 새로 쓰지 마라. 반응 취소 전에는 감점 예정액을 보여주는 경고 확인창을 띄워라. 응답에 내부 회원 ID를 넣지 말고 `is_me`로만 본인을 표시하라. 피드 커서는 `(created_at, id)`로 구현하라. DELETE 요청에도 CSRF 검사를 적용하라. 본인 글 반응 금지, 게시물당 1인 1회, 사진은 게시물별 명시 체크 시에만 공개한다. §3의 TBD는 임의로 확정하지 않는다. 음식은 기존 한식 150종 카탈로그(class_id·food_name·category·unit)만 사용하고, 피드에는 §4-1의 밥·국·반찬 한 상 요약으로 표시한다. 주간 랭킹은 §11-3에 따라 평소 접어 두고 PC에서는 hover·클릭·키보드로, 터치 기기에서는 요약 칩 탭으로 펼친다. feature branch에서 작업하고, §13 테스트와 §15 완료 기준을 통과한 뒤 PR을 올린다.
