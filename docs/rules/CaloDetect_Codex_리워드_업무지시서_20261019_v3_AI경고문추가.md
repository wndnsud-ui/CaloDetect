> **문서 상태 (2026-10-20): 기존 설계·업무지시 참고본.** 현재 구현·후속 결정은 [현재 구현 기준](CURRENT_IMPLEMENTATION.md)과 [개발 규칙](DEVELOPMENT_RULES.md)을 우선한다. 본문의 과거 Stage 진행 상태·닉네임 30일 제한·체형 이미지 금지·Streamlit 관리자·모델 개선 계획은 후속 결정과 충돌하면 적용하지 않는다. 미확정 운영 정책은 [결정 대기 사항](PENDING_DECISIONS.md)을 따른다.

# CaloDetect — Codex CaloPoint · Growth · Reward 업무지시서 (v11 보충, v3)
> 내부 프로젝트 버전: CaloDetect 2.0
> 기준일: 2026-10-19
> 상위 문서: `docs/rules/CaloDetect_Codex_통합_업무지시서_20261002_v11.md` (Master Spec, 원문 수정 금지)
> 선행 문서: `docs/rules/CaloDetect_Codex_커뮤니티_업무지시서_20261015_v5.md` (커뮤니티 포인트 원장·랭킹)
> 기획 근거: `CaloDetect_CaloPoint_Growth_Reward_기획안_v5.md` (이하 "기획안") + 2026-10-19 사용자 결정
> 화면 근거: 디자인 캔버스 "CaloPoint 리워드 시안 v5 · 지방이" (이하 "시안", 번호는 시안의 화면 번호)
> 용도: 식단 기록 포인트 · 성장 XP · 꾸미기 · 리워드 몰 · (플래그 뒤) 실물 교환·쿠폰함 개발 작업 지시
> 이전 버전: v2·v1 (같은 날짜). 변경 이력: `CHANGELOG.md` 참고

## ⚠️ Codex / Claude Code 구현 전 필수 경고

> **구현 전 C1~C13을 먼저 확인하고 파일·라인 근거를 보고할 것. 차단 조건은 임의 해결하지 말고 해당 작업만 중단할 것. Master Spec, 기존 테이블 구조, 기존 API 요청·응답·동작은 변경하지 말 것. 기존 코드 리팩터링 금지. 보상 훅 오류가 식단 저장에 영향을 주지 않도록 SAVEPOINT로 격리할 것. 포인트는 lot·spend·allocation 원장 구조와 FOR UPDATE 잠금 순서를 반드시 유지하고 단순 balance 방식으로 변경하지 말 것. `(user_id, idem_key)` UNIQUE를 중복 지급의 최종 기준으로 사용할 것. Stage A→B→C 순서를 지키고 뒤 Stage 기능을 선구현하지 말 것. TBD 항목은 임의 결정하지 말 것. 온보딩·커뮤니티 포인트의 실물 교환 금지, 랭킹 개인정보 노출 금지, 체중·감량 기반 보상 금지, 플래그 OFF 상태의 Stage C API 동작 금지를 반드시 지킬 것.**

### 특히 주의할 점

- **구현부터 시작하지 말 것:** C1~C13 선확인 → 근거 보고 → 차단 여부 판단 후 구현.
- **기존 코드 정리·리팩터링 금지:** Master Spec, 기존 테이블, 기존 API 응답·동작을 건드리지 말 것.
- **보상 오류와 식단 저장 분리:** 보상 훅은 SAVEPOINT로 격리하고 실패해도 식단 저장은 성공해야 함.
- **포인트 단순 잔액 처리 금지:** lot → spend → allocation 원장 구조를 유지하고 클라이언트 값은 신뢰하지 말 것.
- **동시성 규칙 유지:** `reward_accounts → reward_point_lots → reward_exchange_month_counters → reward_exchanges` 잠금 순서 준수, 잔액 부족 판정은 잠금 이후 수행.
- **중복 지급 방지 기준 유지:** `(user_id, idem_key)` UNIQUE를 최종 기준으로 사용할 것.
- **Stage 혼합 구현 금지:** Stage A → B → C 순서 준수. 후속 Stage 기능을 미리 연결하거나 활성화하지 말 것.
- **TBD 임의 확정 금지:** 문서에 미확정으로 남긴 운영값·정책·기준을 AI가 임의 결정하지 말 것.
- **포인트 출처 구분 유지:** 온보딩·커뮤니티 포인트는 실물·서비스 교환에 사용 금지.
- **보상 규칙 임의 완화 금지:** 끼니당 1회, 오늘·어제만 지급, 동일 SHA-256 사진 재사용 미지급, 3끼 최소 간격, 시드·데모·관리자 식단 미지급 유지.
- **개인정보·건강 윤리 준수:** 랭킹은 닉네임만 사용하고 `user_id`·실명·이메일 노출 금지. 체중·감량량을 보상 조건으로 사용하지 말 것.
- **Stage C 보호:** `REWARD_EXCHANGE_ENABLED=false`일 때 교환 API는 반드시 비활성(404) 상태를 유지할 것.

> **핵심 순서: `C1~C13 확인 → 차단 판단 → 기존 구조 불변 → Stage별 구현`. 문서에 없는 판단을 임의로 추가하지 말 것.**

---

**기획안 v5 대비 2026-10-19 사용자 결정 (본 문서에 반영)**
- **본인인증 제외(이번 범위).** 실물 교환 조건은 "가입 14일 이후 + 월 1회"만 둔다(기획안 7.4·8.2·10장의 본인인증 문구는 이 문서가 대체). 대신 개인정보를 더 받지 않는 대체 장치 3종을 Stage C에 둔다(§2-5).
- **주간 랭킹은 닉네임으로만 표시한다.** 실명(`name`)·이메일은 랭킹에 쓰지 않는다(§6-13).
- **닉네임은 회원가입 마지막 단계에서 정하고, 마이페이지 회원정보에서 바꿀 수 있다**(§6-13, §11-11). 이를 위해 닉네임은 Stage A로 앞당긴다.
- 실물 쿠폰은 **앱 쿠폰함**으로 받는다. 휴대폰 번호·주소 등 추가 개인정보를 받지 않는다.
- 리워드 메뉴는 **리워드 몰 / 지방이 방 / 성장 · 랭킹 / 쿠폰함** 4개 탭으로 구성한다.
- 레벨 전용 배경 5종(LV.1 기본 ~ LV.5 전용 테마)을 둔다. 판매하지 않는다.
- 캐릭터는 사용자 제공 "지방이" 스프라이트 시트를 사용하되, 레벨별 체형 변화 이미지는 결정 전까지 쓰지 않는다(§11-0).

**v2 → v3 변경 요약 (최신)**

| 구분 | v2 | v3 |
|---|---|---|
| 닉네임 시점 | Stage B, 랭킹에서 자동 생성·랭킹 화면에서만 변경 | **Stage A로 이동.** 회원가입 마지막 단계에서 설정(추천 닉네임 미리 채움), 마이페이지 회원정보에서 변경, 랭킹(Stage B)은 표시만 (§1, §5-7, §5-8, §6-13) |
| 가입 흐름 | 변경 없음 | 이메일·구글·카카오 가입 모두 **계정 생성 직후 "닉네임 정하기" 단계** 추가. 기존 가입 API는 바꾸지 않고 로그인된 상태에서 `/rewards/nickname` 호출 (§6-13, §11-11) |
| 기존 회원 | 랭킹 진입 시 자동 생성만 | 자동 생성 + **홈·마이페이지 1회 안내 카드**(닫으면 다시 안 뜸) (§6-13, §11-11) |
| 변경 주기 | 자동 생성에서 첫 변경만 무제한 | **가입 단계·자동 생성 닉네임에서의 첫 직접 변경은 주기 제한 없음**, 그 뒤 30일 1회 (§6-13) |
| 실시간 검사 | 없음(저장 시에만 오류) | `GET /rewards/nickname/check`로 입력 중 검사, 추천 닉네임 다시 뽑기 API (§9) |
| 이름과 닉네임 | — | 마이페이지에서 "이름(커뮤니티 피드에 표시)"과 "닉네임(랭킹에 표시)"을 구분해 안내 (§11-11, §3) |
| 착수 전 확인 | C1~C12 | **C13** 추가: 가입 흐름 3종·마이페이지 수정 코드 위치 (§0) |
| 테스트 | N1~N8 (Stage B) | 닉네임 테스트를 Stage A로 옮기고 N9~N16 추가 (§13) |

**v1 → v2 변경 요약**

| 구분 | v1 | v2 |
|---|---|---|
| 랭킹 표시 | 닉네임 미도입, 기존 `name` 사용 | **닉네임 전용**. 닉네임 테이블·자동 생성·변경 API·금칙어·관리자 초기화 추가 (§5-7, §6-13, §9) |
| 본인인증 대체 | 없음 | 교환 차감 제외 출처(온보딩·커뮤니티), 첫 교환 자동 보류, 월 전체 교환 상한 (§2-5) |
| 캐릭터 | 시트의 레벨 이미지(체형이 작아짐)를 그대로 연결 | 결정 전까지 **전 레벨 같은 정면 이미지**, 성장은 배경·장비로만 표현 (§11-0) |
| 목표·예상 일수 | 기준 잔액·계산식 불명확 | 상품 목표 = 교환 가능 포인트, 아이템 목표 = 총 잔액. 예상 일수 계산식 확정 (§6-12) |
| 주간 미션 | 가입 주에도 5일 필요 | 가입 주는 남은 일수로 조건 축소 (§6-5) |
| 보호권 | 오늘 먼저 기록하면 연속 기록이 끊김 | 오늘 기록 후에도 어제 보호 가능, 연속·보너스 재계산 (§6-3) |
| 구매 차감 순서 | 순수 선입선출 | 꾸미기·보호권 구매는 온보딩 lot 먼저 (§6-9) |
| Stage 구분 | 홈 카드·보상 패널에 Stage B 요소가 섞임 | Stage별 화면 구성 분리, XP는 Stage A부터 적립(화면 비노출) (§6-4, §11-1, §11-2) |
| 누락 정의 | `reward_debts`, 일부 설정값, 테이블별 Stage | 데이터 모델·설정·migration 매핑 추가 (§5-3, §5-6, §5-8) |
| 시안 대조 | — | 시안 문구·수치 수정 목록 추가 (§11-10) |

---

# 0. 착수 전 확인

구현 전에 아래를 확인해 결과와 근거(파일·줄 번호)를 보고한다. "차단"이면 그 항목에 의존하는 작업만 멈추고 보고한다.

| ID | 확인 대상 | 전제 | 다를 때 |
|---|---|---|---|
| C1 | `ROADMAP.md`의 Backlog("포인트·챌린지·광고·파트너십", "Coach/소셜") 및 `PENDING_DECISIONS.md`의 "포인트 사용처 미구현" 조항 | 2026-10-19 사용자 승인으로 본 문서 범위(§1)가 현재 범위로 이동했다는 기록이 있음 | 기록이 없으면 **문서 기록만 먼저** 하고(CHANGELOG·PENDING·ROADMAP), migration·모델 작업은 migration 담당 합의 확인 전까지 **차단** |
| C2 | Alembic 실제 head의 revision 문자열 | 단일 head(현재 `20261016_01` 계열) | 실제 값으로 `down_revision` 지정. 복수 head면 **차단** |
| C3 | **식단이 생성되는 모든 경로**: `POST /meals`(`api.py save_meal`), 채팅 기록 확정(`services/chat_record.py confirm_draft`), 그 밖의 API·스크립트 | 이 두 경로뿐 | 다른 경로가 있으면 목록 보고. 시드·데모 스크립트(`scripts/seed_*`)에서는 **보상을 지급하지 않는다** |
| C4 | **식단 삭제·수정 경로**(히스토리 삭제, 섭취 비율 수정 `consumption_api.py`, 채팅 기록 수정) | 삭제 경로 없음, 섭취 비율 수정만 있음 | 삭제 경로가 있으면 §6-6 회수 규칙을 그 경로에 연결할 위치를 보고(기존 동작 변경 없이 훅만 추가) |
| C5 | 채팅 첨부 사진(`chat_attachments`)이 사진 분석(탐지)을 거치는지, 원본 파일 경로를 서버에서 읽을 수 있는지 | 거치고, 읽을 수 있음 | 아니면 채팅 첨부 식단의 "사진 기록" 판정을 `chat_attachment_id` 존재만으로 할지 보고 |
| C6 | `image_uploads.image_path`·`detection_logs.image_path` 파일을 서버가 다시 읽을 수 있는지(이미지 저장 비활성 환경 포함) | 저장 활성 환경에서 읽을 수 있음 | 저장 비활성 환경이면 사진 해시 검사를 건너뛰고 `photo_hash_unavailable`로 로그만 남김(지급은 정상) |
| C7 | 목표 칼로리·당류·나트륨 기준을 계산하는 기존 함수 위치(`Profile.data`, `services/analytics.py`·`nutrition.py`) | 재사용 가능한 함수가 있음 | 없으면 새로 계산하지 말고 위치 보고. 기준값을 임의로 만들지 않는다 |
| C8 | PostgreSQL 트랜잭션 격리 수준 | READ COMMITTED | 그 이상이면 보고 후 포인트 차감·교환 작업 **차단** |
| C9 | 기존 커뮤니티 포인트 원장(`point_transactions`)·`/community/points/me`·`/community/ranking`을 사용하는 프런트 위치 | `Community.jsx`만 사용 | 다른 곳이 있으면 보고. 기존 API의 응답·동작은 바꾸지 않는다 |
| C10 | 관리자 인증(`security.get_admin`)과 Streamlit 관리자 화면(`streamlit/admin_qa.py`)에 메뉴를 추가할 수 있는 구조인지 | 가능 | 불가하면 Stage C의 관리자 처리를 관리자 API만으로 구현하고 보고 |
| C11 | 음식 카테고리(`foods.category`)로 "채소 포함 끼니"를 판정할 수 있는지 | **불가**(채소 계열 카테고리 4개 음식뿐) | 확인 결과만 보고. 채소 미션은 구현하지 않고 §6-5의 대체 미션을 사용 |
| C12 | 기존 `users`·`Profile.data`에 닉네임·표시명 성격의 필드가 있는지, 커뮤니티 피드·댓글에 `name`이 노출되는 위치 | 닉네임 필드 없음. 피드는 `name` 노출 | 기존 필드가 있으면 **새 테이블을 만들지 말고** 위치와 쓰임을 보고 후 대기. 피드 노출 위치는 목록만 보고(이번 범위에서 바꾸지 않음) |
| C13 | **가입 흐름 3종**의 "가입 성공 → 첫 화면" 이동 위치: 이메일 가입(`main.jsx` 인증 처리·`EmailAuthForm.jsx`), 구글·카카오 가입 완료(`SocialLogin.jsx`의 `onAuthenticated`, 백엔드 `social_auth.py`·`kakao_auth.py`의 가입 완료 단계), 그리고 **마이페이지 회원정보**(`AccountInfo.jsx`) | 세 가입 흐름 모두 가입 직후 로그인된 상태로 프런트에 돌아오고, `AccountInfo.jsx`는 이름·이메일을 읽기 전용으로 표시(2026-10-27 후속 결정: 계정 이름·이메일 변경 불가, `PUT /users/me` 삭제) | 가입 직후 로그인 상태가 아닌 흐름이 있으면 보고(그 흐름은 첫 로그인 시 닉네임 단계를 띄우는 방식으로 대체). 기존 가입·회원정보 API의 요청·응답은 바꾸지 않는다 |

---

# 1. 문서 목적과 범위

식단 기록을 **CaloPoint(사용 가능한 포인트)** 와 **Growth XP(성장 경험치)** 로 보상하고, 포인트를 꾸미기·리워드에 쓰게 한다.

```text
음식 촬영 → 식단 기록 → CaloPoint + Growth XP
→ 첫날 꾸미기 → 연속 기록·미션·레벨업 → 레벨 전용 배경
→ (Stage C, 플래그) 건강상품 교환 신청 → 쿠폰함
```

작업은 3단계로 나눈다. 각 Stage는 별도 PR로 올리고, 앞 Stage가 병합된 뒤 다음 Stage를 시작한다.

| Stage | 기획안 Phase | 내용 | 기본 상태 |
|---|---|---|---|
| **A** | Phase 1 | 포인트 원장(적립 건별), 식단 기록 포인트, 온보딩 포인트, 스타터 아이템 6종 구매·착용, 홈 리워드 카드(A 구성), 기록 직후 보상 패널(A 구성), 회수 UX, **닉네임(가입 단계 설정·마이페이지 변경·기존 회원 안내)**. **XP는 원장에만 적립하고 화면에는 보이지 않음**(§6-4) | 활성 |
| **B** | Phase 2 + 3 | Growth XP 화면·레벨·레벨업 보상, 연속 기록·보호권, 오늘의·주간 미션, 주간 랭킹(건강 XP·닉네임 표시, 랭킹에서 닉네임 바꾸기 진입점), 레벨 전용 배경·지방이 방, 꾸미기 몰 확장, 목표 리워드, 커뮤니티 반응 보상 XP 전환 | 활성 |
| **C** | Phase 4 MVP | 건강상품 교환 신청(운영자 수동 쿠폰 발급), 쿠폰함, 교환 취소, 관리자 처리 화면 | **`REWARD_EXCHANGE_ENABLED=false`** — 재원·제휴 확정 전 비활성 |

다음은 구현하지 않는다.

```text
AI 분석·코칭·전문가 서비스의 실제 제공(Phase 5) — 리워드 몰에 "준비 중" 상품으로만 노출
포인트 현금 구매·현금 환급
본인인증, 휴대폰 번호·배송지 수집
제휴사 쿠폰 API 자동 연동, 쿠폰 사용 여부 자동 수신
푸시·이메일 알림(만료 예정 안내, 쿠폰 발급 안내 포함) — 화면 표시만
커뮤니티 피드·댓글의 닉네임 적용 (§3 TBD) — 이번에는 랭킹에만 닉네임
목표 칼로리 하한 강제 (§3 TBD)
데이터 기반 상품 추천 2단계(탄단지 목표 필요)
```

---

# 2. 확정 사항

## 2-1. 재화

| 항목 | 결정 |
|---|---|
| CaloPoint | 사용 가능한 재화. 적립 건별 원장, 유효기간 12개월, 선입선출(만료일 빠른 건부터) 차감 |
| Growth XP | 성장 전용. 사용 불가, 부정 적립 회수 외에는 줄지 않음. 레벨은 내려가지 않음 |
| 온보딩 포인트 | 꾸미기·보호권에만 사용. 실물·서비스 교환 시 차감 대상에서 제외 |
| 교환 제외 출처 | `REWARD_EXCHANGE_EXCLUDED_SOURCES`(기본 `onboarding,community,community_legacy`)에 든 lot은 실물·서비스 교환에 쓰지 않는다. 꾸미기·보호권에는 쓸 수 있다 |
| 교환 가능 포인트 | 유효한 lot 중 교환 제외 출처가 아닌 lot의 `remaining` 합계 |
| 화면 표시 | 총 잔액 1개 + 교환 화면에서 "실물 교환에 쓸 수 있는 포인트"를 따로 표시. 제외분은 "꾸미기 전용 nP"로 한 줄 표시 |

## 2-2. 수치 (기획안 부록 A — 모든 값은 설정으로 둔다, §5-6)

| 분류 | 항목 | 포인트 | XP | 한도 |
|---|---|---:|---:|---|
| 온보딩 | 회원가입 / 목표 설정 / 첫 식단 기록 | 10 / 10 / 10 | — | 각 1회 |
| 일일 | 아침·점심·저녁 기록 (사진) | 2 | 10 | 끼니당 1회 |
| 일일 | 아침·점심·저녁 기록 (사진 없음) | 1 | 10 | 끼니당 1회 |
| 일일 | 간식 기록 | 1 | 5 | 1일 1회 |
| 일일 | 하루 3끼 완료 | 3 | 10 | 1일 1회 |
| 일일 | 오늘의 미션 | 2 | 10 | 1일 1회 |
| 일일 | 커뮤니티 식단 공유 | 1 | 10 | 1일 1회 (Stage B부터) |
| 일일 | 영양 균형 달성 | — | 15 | 1일 1회 |
| 보너스 | 연속 기록 3일째 / 7일째 (7일 주기 반복) | 5 / 10 | 20 / 50 | 해당 일 1회 |
| 보너스 | 주간 미션 / 월간 목표 | 15 / 30 | — | 주 1회 / 월 1회 |
| 커뮤니티 | 좋아요 받기 / 추천 받기 / 반응 누르기 | — | 5 / 10 / 2 | 받기 합산 일 50, 누르기 일 20 |
| 레벨 | LV.2 / 3 / 4 / 5 누적 XP | — | 300 / 1,000 / 2,500 / 5,000 | — |
| 레벨업 | LV.3 / 4 / 5 포인트 | 50 / 100 / 200 | — | 1회 |

## 2-3. 공통 지급 규칙

| 규칙 | 내용 |
|---|---|
| 끼니당 1회 | 같은 날 같은 끼니는 여러 번 기록해도 1회 지급 |
| 사진 판정 | 식단 항목 중 하나라도 `detection_log_id`가 있거나 `chat_attachment_id`가 있으면 사진 기록(C5 결과 반영). 경로(사진/채팅)는 따지지 않는다 |
| 기록 인정 기간 | `meal_date`가 KST 오늘 또는 어제일 때만 지급·연속 기록 반영. 그 이전 날짜는 기록만 저장 |
| "기록한 날" | 그 날짜에 보상 지급된 기록이 1개 이상 |
| 온보딩 + 일일 | 첫 식단 기록 시 온보딩 +10과 끼니 +2를 모두 지급 |
| 같은 사진 재사용 | 이미 보상에 쓰인 사진과 SHA-256이 같으면 끼니 포인트·XP 미지급(기록은 저장). 회원 구분 없이 검사 |
| 3끼 완료 간격 | 세 끼의 **기록 시각**(created_at) 사이 간격이 모두 `REWARD_THREE_MEAL_MIN_GAP_MINUTES` 이상일 때만 지급 |
| 섭취 비율 0 | 지급한다(정직한 기록 장려, §3 TBD로 기록) |
| 시드·데모·관리자 생성 식단 | 지급하지 않는다 |

## 2-4. 건강 윤리 원칙 (구현에 반드시 반영)

```text
적게 먹을수록 더 받는 보상 없음 — 칼로리 관련 보상은 항상 "목표 ±15% 범위 안"
체중은 어떤 보상 조건에도 쓰지 않는다
간식·과식 끼니도 똑같이 지급
연속 기록이 끊겨도 부정 문구 금지 — "다시 시작해요" 류의 회복 문구만
레벨 이미지·문구에 체형 비하 표현 금지 (§3 캐릭터 시트 검토 참조)
```

## 2-5. 실물 교환 (Stage C)

| 항목 | 결정 |
|---|---|
| 조건 | 가입 14일 이후(KST 날짜 기준) + KST 달력월 기준 월 1회. **본인인증 없음** |
| 사용 포인트 | 교환 제외 출처(§2-1)를 뺀 적립 건에서 선입선출 차감 |
| 본인인증 대체 ① | 커뮤니티 반응으로 생긴 포인트(`community`, `community_legacy`)는 교환에 쓰지 않는다. 계정끼리 반응을 주고받아 실물을 만드는 경로를 막는다 |
| 본인인증 대체 ② | 회원의 **첫 교환 신청은 자동으로 `held`(보류)** 로 들어가 운영자가 확인 후 발급한다(`REWARD_EXCHANGE_FIRST_HOLD=true`). 두 번째부터는 `requested` |
| 본인인증 대체 ③ | **월 전체 교환 상한** `REWARD_EXCHANGE_GLOBAL_MONTHLY_CAP`(KST 달력월, 활성 상태 건수 기준). 값이 없거나 0 이하이면 플래그가 켜져 있어도 교환 기능을 끈 것으로 취급하고 시작 로그에 경고(교환 API 404). 상한 도달 시 신청 거부 |
| 수령 | 앱 쿠폰함. 추가 개인정보 수집 없음 |
| 처리 | 신청 → 운영자가 관리자 화면에서 쿠폰 번호 입력해 발급 → 쿠폰함 |
| 취소 | 발급 전 사용자 취소 가능, 포인트 전액 반환, **그 달 교환 횟수도 복원** |
| 발급 실패 | 운영자가 실패 처리 시 포인트 전액 자동 반환 |
| 발급 후 | 취소 불가. 사용 표시는 사용자가 "이미 사용했어요"로 직접 표시 |
| 이상 패턴 | 운영자가 "보류" 처리 가능. 자동 탐지는 로그 지표만(§7) |

---

# 3. 미확정 항목 — TBD 유지

임의로 확정하지 않는다. 개발 기본값은 설정으로만 두고 운영 확정값처럼 표시하지 않는다.

| 항목 | 개발 처리 |
|---|---|
| 모든 수치(§2-2) | 설정 기본값. 화면에 "개발 중 기준" 표시 안 함(커뮤니티와 달리 사용자용 확정 문구로 보이므로, 운영 전 수치 확정 필요) |
| 3끼 최소 간격 | 기본 120분 |
| 미션 문구·조건 | §6-5 대체 미션만. 채소 미션은 음식 태그 체계 확정 후(C11). 주간 미션 일수(5일)·가입 주 축소 규칙도 설정값 |
| 목표 칼로리 하한 | 미적용. `GOAL_CALORIE_FLOOR` 없음 → 영양 균형 XP는 저장된 목표 그대로 사용 |
| 저섭취 패턴 안내 | 미구현(기준값 전문가 검토 후) |
| 닉네임 금칙어 목록 | `backend/app/data/nickname_blocklist.txt`(한 줄에 한 단어) 파일만 만들고 **내용은 운영 확정 전 최소 예시만**. 운영 확정 목록은 TBD |
| 닉네임 변경 주기 | 기본 30일 1회(`REWARD_NICKNAME_CHANGE_DAYS`). 운영 확정 TBD |
| 커뮤니티 피드·댓글 닉네임 | 이번 범위 아님. 피드는 기존 `name` 그대로(C12 보고만) |
| 이름과 닉네임 이원화 | 피드는 `name`, 랭킹은 닉네임으로 표시가 나뉜다. 이번에는 마이페이지에서 두 값의 쓰임을 문구로 구분해 안내만 하고(§11-11), 하나로 합칠지는 TBD |
| 가입 단계 건너뛰기 | 허용하지 않는다(추천 닉네임 확정이 기본 동작). 가입 단계 이탈 시 1회 재표시 후 자동 생성 유지(§6-13) |
| 기존 `/community/ranking` | 응답 불변 원칙에 따라 남겨 두되, Stage B부터 **화면에서 호출하지 않는다**. 엔드포인트 정리(폐기)는 TBD |
| 캐릭터 시트와 기획 원칙 충돌 | 시트의 레벨 이미지는 체형이 작아지는 구성이라 기획안 5.3과 충돌. **결정 전까지 레벨별 체형 이미지는 쓰지 않는다**(§11-0). 레벨 이름은 기획안(시작/기록하는/움직이는/균형 잡힌/건강 습관). 시트 문구("예뻐지는", "가벼워진 몸")는 화면에 쓰지 않는다 |
| 캐릭터 이름 "지방이" | 기획안 5.4의 사용자 테스트 대상. 화면 문구의 캐릭터 이름은 프런트 상수 1곳(`Jibang.jsx`의 `CHARACTER_NAME`)에서만 가져온다 |
| 앨범·과거 사진 | 촬영 시각 검증(기획안 부록 B 6번) 미결. 이번에는 앨범 사진도 사진 기록으로 지급하고, 사진 메타데이터는 저장하지 않는다 |
| 사진 재사용 검사의 한계 | SHA-256은 똑같은 파일만 잡는다(다시 저장·자르기는 통과). 유사 이미지 검사는 TBD |
| 실물 교환 재원·제휴사·상품 단가·쿠폰 유효기간 | Stage C는 플래그 비활성. 상품명·이미지 자리는 `[제휴사명]` 등 자리표시자 |
| 본인인증 대체 장치 값 | 교환 제외 출처·첫 교환 보류는 기본 켜짐, 월 전체 상한 값은 **플래그를 켜기 전 운영 확정**(미설정이면 교환 꺼짐) |
| 이상 패턴 자동 탐지 기준 | 미구현, 지표만 로그 |
| 같은 기기 다계정 교환 보류 | 기기 식별 수단 없음. 미구현(첫 교환 보류로 운영자 확인) |
| 만료 30일 전 안내 | 화면 배지만(알림 없음) |
| 식단 삭제 시 회수 | 현재 삭제 경로 없음(C4). 경로가 생기면 §6-6 적용 |
| 전문가 서비스 실제 단가 | Phase 5, 미구현 |

---

# 4. 절대 금지 사항

```text
Master Spec 원문 수정 금지
기존 테이블 컬럼 변경·삭제 금지 (새 테이블만 추가)
기존 API의 응답·동작 변경 금지 — /meals, /community/points/me, /community/ranking 포함
  (식단 저장 경로에는 §6-1의 보상 훅 호출 1줄만 추가)
보상 지급 실패가 식단 저장을 실패시키는 구조 금지 (SAVEPOINT로 격리)
포인트 잔액을 원장 없이 덮어쓰기 금지 (캐시는 원장에서 재계산 가능해야 함)
클라이언트가 보낸 포인트·가격·XP·잔액 신뢰 금지
교환 제외 출처(온보딩·커뮤니티) 포인트를 실물·서비스 교환에 차감 금지
랭킹 응답·화면에 name·이메일·회원 ID 사용 금지 (닉네임만)
닉네임을 로그에 남기는 것 금지
레벨별 체형 변화 이미지(시트의 LV.1·3·4·5 몸) 화면 사용 금지 (§11-0, 결정 전까지)
체중·감량을 보상 조건에 사용 금지
현금 결제·현금 환급 경로 생성 금지
본인인증·휴대폰 번호·주소 수집 금지
Stage C 플래그가 꺼져 있을 때 교환 API가 동작하는 것 금지 (404)
쿠폰 번호를 로그·랭킹·커뮤니티 응답에 노출 금지
DB 방언(SQLite/PostgreSQL) 분기로 잠금 규칙을 다르게 구현 금지
FK CASCADE 금지
본 문서 범위 밖(AI·코칭 제공, 알림, 피드 닉네임)의 빈 Route·빈 파일 선생성 금지
```

---

# 5. 데이터 모델

새 파일 `backend/app/models_rewards.py`에 정의하고 `models.py`의 `Base`를 공유한다. 모든 시각은 timezone-aware UTC, 날짜 판정은 `services/timezone.korean_date`.

## 5-1. reward_accounts (회원별 잠금·캐시)

| 컬럼 | 설명 |
|---|---|
| `user_id` PK, FK users | |
| `balance_cache` int | 사용 가능 포인트 합계 캐시. 원장과 다르면 원장 기준 재계산 |
| `xp_total_cache` int | XP 합계 캐시 |
| `level` int | 지금 레벨(내려가지 않음) |
| `goal_ref` str nullable | 목표 리워드(`item:<id>` / `product:<id>`) |
| `created_at`, `updated_at` | |

포인트 차감·교환·구매는 **항상 이 행을 먼저 `FOR UPDATE`** 로 잠근다(§6-0).

## 5-2. reward_point_lots (적립 건)

| 컬럼 | 설명 |
|---|---|
| `id` uuid | |
| `user_id` FK | |
| `source` enum str | `onboarding` `meal` `bonus` `mission` `community` `community_legacy` `levelup` `refund` `adjust` |
| `amount` int (>0) | 적립액 |
| `remaining` int (0~amount) | 남은 금액 |
| `earned_at`, `expires_at` | `expires_at = earned_at + REWARD_POINT_VALID_DAYS` |
| `ref_type`, `ref_id` | 근거(meal, reaction, level, exchange 등) |
| `idem_key` str | 중복 지급 방지 키(§6-2) |
| UNIQUE(`user_id`, `idem_key`) | |
| CHECK `remaining >= 0 AND remaining <= amount` | |

## 5-3. reward_point_spends / reward_point_allocations (차감)

`reward_point_spends`: `id`, `user_id`, `kind`(`item` `exchange` `expire` `revoke`), `amount`, `ref_type`, `ref_id`, `created_at`.
`reward_point_allocations`: `spend_id`, `lot_id`, `amount` — 어느 적립 건에서 얼마를 썼는지. 환불은 allocation을 거꾸로 따라 해당 lot의 `remaining`을 복원한다(만료된 lot이면 새 `refund` lot 생성, 유효기간 새로 시작). 새 `refund` lot은 **원래 lot의 출처 제한을 이어받는다**(`refund` lot에 `restricted` bool을 두고, 원래 lot이 교환 제외 출처였으면 true).

`reward_debts`: `id`, `user_id`, `amount`(>0), `remaining`, `reason`(`revoke`), `ref_type`, `ref_id`, `created_at`. 회수할 포인트가 잔액보다 많을 때 기록하고, 다음 적립 시 같은 트랜잭션에서 먼저 상계한다(상계분은 `revoke` spend + allocation으로 남김). 잔액은 음수가 되지 않는다.

## 5-4. reward_xp_events (XP 원장)

| 컬럼 | 설명 |
|---|---|
| `id`, `user_id`, `amount`(음수는 회수만) | |
| `source` | `meal` `snack` `three_meals` `mission` `balance` `streak` `share` `reaction_received` `reaction_given` `revoke` |
| `counts_for_ranking` bool | 커뮤니티 반응 XP(`reaction_*`)와 `share`는 false |
| `event_date` date (KST) | 일 상한·주간 집계 기준 |
| `ref_type`, `ref_id`, `idem_key` | UNIQUE(`user_id`, `idem_key`) |

## 5-5. 아이템

`reward_items` (시드): `id` slug, `name`, `kind`(`deco` `protector` `background`), `slot`(`hat` `glasses` `ribbon` `shoes` `sticker` `background` `prop` `none`), `price` nullable, `level_required` nullable, `sellable` bool, `stage`(A/B), `asset_key`, `active`.

시드 목록:

| id | 이름 | kind/slot | 가격 | 비고 |
|---|---|---|---:|---|
| `starter_sticker` | 기본 스티커 | deco/sticker | 10 | Stage A |
| `starter_glasses` | 기본 안경 | deco/glasses | 10 | Stage A |
| `starter_ribbon` | 리본 | deco/ribbon | 10 | Stage A |
| `starter_hat` | 기본 모자 | deco/hat | 20 | Stage A |
| `starter_shoes` | 운동화 | deco/shoes | 20 | Stage A |
| `starter_bg` | 기본 배경 | background | 30 | Stage A (판매형 배경) |
| `prop_water` / `prop_salad` / `prop_heart` | 물병 소품 / 샐러드 볼 소품 / 하트 쿠션 | deco/prop | 40 / 50 / 60 | Stage B |
| `outfit_workout` | 운동복 세트 | deco/prop | 80 | Stage B |
| `season_set` | 한정판 시즌 세트 | deco/prop | 150 | Stage B, `active=false` 기본 |
| `protector` | 연속 기록 보호권 | protector | 30 | Stage B, 월 2회 |
| `bg_lv1`~`bg_lv5` | 포근한 아침 방 / 새싹 정원 / 산책 공원 / 텃밭 피크닉 / 햇살 언덕 | background | — | `sellable=false`, `level_required` 1~5 |
| `outfit_lv3`, `costume_lv4`, `title_lv5` | 레벨 전용 의상·코스튬·칭호 | deco | — | `sellable=false` |

`reward_user_items`: `user_id`, `item_id`, `quantity`(보호권만 >1), `acquired_via`(`purchase` `level` `default`), `created_at`. UNIQUE(`user_id`,`item_id`).
`reward_equipment`: `user_id`, `slot`, `item_id`. PK(`user_id`,`slot`).
`reward_streak_protections`: `user_id`, `protected_date`, `created_at` — 보호권 사용 기록(월 2회 검사용). UNIQUE(`user_id`,`protected_date`).

기타 보조 테이블(본문에서 정의): `reward_photo_hashes`(§6-1), `reward_grant_batches`(§6-1), `reward_level_events`(§6-4), `reward_products`·`reward_exchanges`(§6-11).

## 5-7. reward_nicknames (Stage A)

| 컬럼 | 설명 |
|---|---|
| `user_id` PK, FK users | |
| `nickname` str | 화면 표시값(앞뒤 공백 제거, NFC 정규화) |
| `nickname_key` str UNIQUE | 중복 검사 키: NFC + 소문자 + 공백 제거 |
| `generated` bool | 자동 생성 닉네임이면 true |
| `set_via` str | 마지막으로 값을 정한 경로: `generated` `signup` `account` `ranking` `admin_reset` |
| `changed_at` timestamptz nullable | 변경 주기 계산 기준 시각. **가입 단계 설정·자동 생성·관리자 초기화는 갱신하지 않음**(null 유지), 마이페이지·랭킹에서 직접 바꿀 때만 갱신 |
| `prompt_dismissed_at` timestamptz nullable | 기존 회원 대상 "닉네임 정하기" 안내 카드를 닫은 시각(§11-11) |
| `created_at`, `updated_at` | |

기존 `users` 테이블은 건드리지 않는다(C12).

## 5-8. migration과 테이블 매핑

| migration | 테이블 |
|---|---|
| `20261019_01_rewards` (A) | `reward_accounts`, `reward_point_lots`, `reward_point_spends`, `reward_point_allocations`, `reward_debts`, `reward_xp_events`, `reward_items`, `reward_user_items`, `reward_equipment`, `reward_photo_hashes`, `reward_grant_batches`, `reward_nicknames` + 데이터 단계(`community_legacy` 이관) |
| `…_02_rewards_growth` (B) | `reward_level_events`, `reward_streak_protections` |
| `…_03_rewards_exchange` (C) | `reward_products`, `reward_exchanges`, `reward_exchange_month_counters` |

`reward_xp_events`는 Stage A에 만든다. XP는 A부터 쌓이고 화면 표시만 B부터다(§6-4).

## 5-6. 설정 (`config.py`, 기본값 = 기획안 부록 A)

```text
REWARD_ENABLED=true
REWARD_POINT_VALID_DAYS=365
REWARD_MEAL_PHOTO_POINTS=2, REWARD_MEAL_TEXT_POINTS=1, REWARD_MEAL_XP=10
REWARD_SNACK_POINTS=1, REWARD_SNACK_XP=5
REWARD_THREE_MEALS_POINTS=3, REWARD_THREE_MEALS_XP=10, REWARD_THREE_MEAL_MIN_GAP_MINUTES=120
REWARD_ONBOARDING_SIGNUP=10, REWARD_ONBOARDING_GOAL=10, REWARD_ONBOARDING_FIRST_MEAL=10
REWARD_DAILY_MISSION_POINTS=2, REWARD_DAILY_MISSION_XP=10
REWARD_WEEKLY_MISSION_POINTS=15, REWARD_MONTHLY_GOAL_POINTS=30
REWARD_STREAK3_POINTS=5, REWARD_STREAK3_XP=20, REWARD_STREAK7_POINTS=10, REWARD_STREAK7_XP=50
REWARD_BALANCE_XP=15, REWARD_BALANCE_CAL_TOLERANCE=0.15
REWARD_SHARE_POINTS=1, REWARD_SHARE_XP=10
REWARD_REACTION_RECEIVED_LIKE_XP=5, REWARD_REACTION_RECEIVED_RECOMMEND_XP=10, REWARD_REACTION_RECEIVED_DAILY_CAP=50
REWARD_REACTION_GIVEN_XP=2, REWARD_REACTION_GIVEN_DAILY_CAP=20
REWARD_LEVEL_THRESHOLDS=0,300,1000,2500,5000
REWARD_LEVELUP_POINTS=0,0,50,100,200
REWARD_PROTECTOR_MONTHLY_LIMIT=2
REWARD_ONBOARDING_START_AT=<배포 시각, 필수. 없으면 가입 온보딩 지급 안 함>
REWARD_WEEKLY_MISSION_DAYS=5
REWARD_ETA_WINDOW_DAYS=7
REWARD_RANKING_SIZE=10
REWARD_NICKNAME_MIN_LEN=2, REWARD_NICKNAME_MAX_LEN=12, REWARD_NICKNAME_CHANGE_DAYS=30
REWARD_NICKNAME_CHECK_PER_MIN=30, REWARD_NICKNAME_SUGGEST_PER_MIN=10
REWARD_COMMUNITY_XP_MODE=false        # Stage B 전환 스위치(§6-7)
REWARD_EXCHANGE_ENABLED=false         # Stage C
REWARD_EXCHANGE_MIN_ACCOUNT_DAYS=14, REWARD_EXCHANGE_MONTHLY_LIMIT=1
REWARD_EXCHANGE_EXCLUDED_SOURCES=onboarding,community,community_legacy
REWARD_EXCHANGE_FIRST_HOLD=true
REWARD_EXCHANGE_GLOBAL_MONTHLY_CAP=   # 기본 없음. 없거나 0 이하이면 교환 꺼짐(§2-5)
```

---

# 6. 규칙

## 6-0. 공통 잠금·트랜잭션 규칙

```text
지급: 같은 트랜잭션에서 lot/xp 행 INSERT. 중복은 UNIQUE(user_id, idem_key)로만 막는다
      (IntegrityError → 해당 지급만 건너뜀, SAVEPOINT 사용)
차감(구매·교환·만료·회수): reward_accounts 행 FOR UPDATE → lots를 expires_at, earned_at, id 순으로 FOR UPDATE
      → allocation 작성 → remaining 감소 → balance_cache 갱신 → commit
잔액 부족 판정은 잠금 이후에 한다
잠금 순서: reward_accounts → reward_point_lots → (교환) reward_exchange_month_counters → reward_exchanges
식단 저장 경로의 보상 훅은 db.begin_nested() 안에서 실행. 예외 시 rollback to savepoint,
      로그 "reward grant failed"(회원·식단 ID 제외)만 남기고 식단 저장은 계속
```

## 6-1. 식단 보상 훅

`services/rewards.py`의 `grant_for_meal(db, user, meal)`을 **C3에서 확인한 식단 생성 경로 두 곳**에서, 식단 `flush()` 직후·commit 이전에 호출한다(기존 로직 순서·응답 불변).

처리 순서:

```text
1. meal_date가 KST 오늘/어제가 아니면 종료
2. 사진 판정(§2-3), 사진이면 원본 파일 SHA-256 계산 → reward_photo_hashes에 이미 있으면 끼니 보상 없이 3번 이후 진행
   (reward_photo_hashes: sha256 UNIQUE, user_id, meal_id — 새 테이블)
3. 끼니 지급: breakfast/lunch/dinner → idem "meal:{date}:{type}", snack → "snack:{date}"
4. 온보딩 첫 기록: idem "onboarding:first_meal"
5. 3끼 완료 검사: 세 끼가 모두 지급됐고 간격 조건 충족 → idem "three:{date}"
6. 연속 기록 갱신 → 3일째/7일째(7일 주기)면 idem "streak3:{date}" / "streak7:{date}"
7. 오늘의 미션·주간 미션·월간 목표 검사(§6-5)
8. XP 합계로 레벨 재계산 → 오르면 §6-4
```

결과는 `reward_grant_batches`(id, user_id, meal_id, created_at)로 묶어, 프런트가 `GET /rewards/grants?meal_id=`로 "방금 받은 보상"을 조회한다(§9). **`POST /meals` 응답은 바꾸지 않는다.**

## 6-2. 온보딩 지급

| 시점 | idem | 연결 위치 |
|---|---|---|
| 가입 완료 | `onboarding:signup` | 가입 성공 후(이메일·구글·카카오 모두). 기존 가입 코드에 훅 1줄 |
| 목표 설정 저장 | `onboarding:goal` | `PUT /users/me/profile` 첫 저장 성공 후 |
| 첫 식단 기록 | `onboarding:first_meal` | §6-1 |

기존 회원(출시 이전 가입자)은 가입·목표 온보딩을 소급 지급하지 않는다. `REWARD_ONBOARDING_START_AT` 이후 가입자에게만 가입 보상.

## 6-3. 연속 기록 · 보호권

- 연속 일수 = 오늘(또는 오늘 기록 전이면 어제)부터 거꾸로 "기록한 날" 또는 "보호된 날"이 이어진 일수.
- 보너스는 연속 일수가 3, 7, 10, 14, 17, 21 … 일 때(즉 `n % 7 in {3, 0}`) 그 날짜 키로 1회.
- 보호권: 어제가 기록 없는 날이고 보호권이 있으면 `POST /rewards/streak/protect`로 어제를 보호(월 2회). 보호된 날은 보너스 카운트에 포함하되 끼니 보상은 없음.
- **오늘 이미 기록한 뒤에도 어제를 보호할 수 있다**(KST 오늘 23:59까지). 보호하면 연속 일수를 다시 계산하고, 그 결과 오늘 연속 일수가 보너스 대상(3·7·10·14…)이 되면 오늘 날짜 키로 보너스를 지급한다(idem 키가 같으므로 중복 없음).
- 홈·기록 직후 패널은 "어제를 놓쳤어요 · 보호권으로 n일 연속을 이어갈 수 있어요"를 보호권 보유 시에만 표시한다. 보호권이 없으면 회복 문구만.
- 보호권 사용은 `reward_user_items.quantity` 차감과 `reward_streak_protections` INSERT를 한 트랜잭션에서 한다(`reward_accounts` FOR UPDATE 먼저).
- 끊김 문구: "다시 시작해요" 류만(§2-4).

## 6-4. 레벨업

```text
XP 합계가 다음 임계값 이상이면 level 상승 (여러 단계 동시 상승 가능)
레벨마다 1회: 포인트(idem "level:{n}") + 레벨 전용 아이템 지급(acquired_via=level)
  LV.2 bg_lv2 / LV.3 outfit_lv3 + bg_lv3 + 50P / LV.4 costume_lv4 + bg_lv4 + 100P / LV.5 title_lv5 + bg_lv5 + 200P
bg_lv1은 가입 시 default 지급·기본 장착
레벨업 이벤트는 reward_level_events(user_id, level, seen_at nullable)에 기록 → 프런트가 미확인 이벤트로 축하 창 표시(§11-4)
XP 회수로 합계가 임계값 아래로 내려가도 level·지급 아이템은 유지
```

**Stage A의 XP**: Stage A에서도 §2-2의 XP를 `reward_xp_events`에 적립하되 레벨 계산·레벨업 지급·화면 표시는 하지 않는다. Stage B 배포 시 data migration 단계가 아니라 **첫 `/rewards/me` 또는 보상 훅 실행 시점**에 회원별로 레벨을 계산해 레벨업 보상을 지급한다(idem 키로 1회). 이때 생긴 레벨업 이벤트는 **가장 높은 레벨 1건만** 미확인으로 두고 나머지는 `seen_at`을 채워 축하 창이 여러 번 뜨지 않게 한다.

## 6-5. 미션 (대체 미션 — C11 결과로 채소 미션 대신 사용)

| 종류 | 조건 | 보상 |
|---|---|---|
| 오늘의 미션 | 그 날 사진 기록 끼니(아침·점심·저녁·간식) 2개 이상 | +2P, +10 XP (idem `mission:{date}`) |
| 주간 미션 | KST 월~일 중 기록한 날 `REWARD_WEEKLY_MISSION_DAYS`(5)일 이상. **가입한 주**는 조건을 `min(5, 가입일~그 주 일요일 일수)`로 줄인다 | +15P (idem `weekly:{iso_week}`) |
| 월간 목표 | 그 달 기록한 날 20일 이상. 가입한 달은 `min(20, 가입일~말일 일수 − 2)` (최소 1) | +30P (idem `monthly:{yyyy-mm}`) |

- 오늘의 미션은 끼니 보상과 **같은 저장에서 함께 지급될 수 있다**(두 번째 사진 끼니 저장 시). 이 경우 같은 `reward_grant_batches`에 묶여 기록 직후 패널에 함께 표시된다(§11-2).
- 미션 정의는 `services/reward_rules.py`의 상수 목록으로 두고, 화면 문구는 API에서 내려준다(프런트 하드코딩 금지).

## 6-6. 회수

- 식단 삭제(경로가 생기면): 그 식단을 ref로 한 끼니·온보딩 제외 지급을 회수. lot이 남아 있으면 remaining 감소, 이미 썼으면 `revoke` spend로 잔액 차감, 잔액이 부족하면 음수 잔액을 만들지 않고 `reward_debts`에 기록 후 다음 적립에서 상계(§6-0 순서).
- 3끼·연속·미션은 회수하지 않는다(지급 시점 조건으로 확정).
- 섭취 비율 수정은 회수 대상이 아니다.
- 회수 전 화면에 예상 회수액을 보여주는 확인창(커뮤니티 감점 확인창 재사용).

## 6-7. 커뮤니티 포인트 연결

**Stage A**: 기존 `services/community.py`의 지급·감점 로직은 그대로 둔다. 같은 트랜잭션 안에서 반응 지급 시 `community` lot(idem `reaction:{reaction_id}:{reason}`)을, 감점 시 같은 lot 회수를 추가한다. 출시 시점의 기존 커뮤니티 잔액은 migration 데이터 단계에서 회원별 `community_legacy` lot 1건으로 옮긴다(잔액 ≤ 0이면 생성 안 함).
**Stage B**: `REWARD_COMMUNITY_XP_MODE=true`로 전환한다. 이때부터 반응은 포인트 대신 XP(일 상한 적용), 식단 공유는 +1P·+10 XP. 기존 커뮤니티 포인트 설정값은 0으로 운영하고, 기존 `point_transactions` 원장과 기존 API는 그대로 둔다(과거 내역 표시용).
**Stage C 착수 조건**: XP 전환이 운영에 적용되어 있어야 한다. `community`·`community_legacy` lot은 전환 전후 모두 교환 제외 출처다(§2-1). 꾸미기·보호권에는 쓸 수 있다.

## 6-8. 만료

- 잔액 조회·차감 시점에 `expires_at < now`인 lot을 `expire` spend로 0 처리(지연 처리, 배치 불필요).
- 30일 이내 만료 예정 합계를 `/rewards/me`에 포함해 화면 배지로 표시.

## 6-9. 구매·장착

- 구매: `sellable=true`, `active=true`, 레벨 조건 충족, 미보유(보호권 제외)일 때만.
- 꾸미기·보호권 구매의 차감 순서: **교환 제외 출처 lot(온보딩 → 커뮤니티 계열) 먼저**, 그 안에서 만료일 순. 남은 금액은 나머지 lot에서 만료일 순. 쓰임이 제한된 포인트를 먼저 써서 교환 가능 포인트를 지키기 위해서다. 실물·서비스 교환은 제외 출처를 쓰지 않는다(§2-5).
- 구매 응답과 구매 창에는 "가입 보너스·커뮤니티 포인트 nP가 먼저 사용돼요"를 실제 배분 결과로 표시한다.
- 디지털 아이템 환불 없음.
- 장착: 보유 아이템만, slot당 1개. 배경 slot은 `background` 아이템.

## 6-10. 랭킹 (Stage B)

- `GET /rewards/ranking`: 이번 주(KST 월요일 00:00~) `counts_for_ranking=true` XP 합계, 동점 동순위, 상위 `REWARD_RANKING_SIZE`명 + 내 순위.
- 응답 항목: `rank`, `nickname`, `xp`, `is_me`. **회원 ID·`name`·이메일 없음.** 닉네임이 없는 회원은 랭킹 계산 시 자동 생성한다(§6-13).
- 이번 주 XP가 0인 회원은 랭킹에 넣지 않는다.
- 커뮤니티 화면의 주간 랭킹 표시는 Stage B에서 이 API로 바꾼다. 기존 `/community/ranking`은 응답을 바꾸지 않고 남겨 두되 화면에서는 호출하지 않는다.

## 6-11. 실물 교환 · 쿠폰 (Stage C, 플래그)

`reward_products`(시드): `id`, `name`, `category`(`goods` `ai` `pro`), `price`, `available`(ai·pro는 false = "준비 중"), `partner_label`.
`reward_exchanges`: `id`, `user_id`, `product_id`, `points`, `status`(`requested` `held` `issued` `used` `canceled` `failed`), `requested_at`, `issued_at`, `coupon_code_enc`, `coupon_expires_at`, `used_marked_at`, `month_key`(KST yyyy-mm), `spend_id`.

```text
신청: 플래그·월 전체 상한 설정·가입 14일·이번 달 활성 교환(requested/held/issued/used) 0건
      ·월 전체 활성 교환 수 < REWARD_EXCHANGE_GLOBAL_MONTHLY_CAP·교환 가능 포인트 확인
      → §6-0 차감(교환 제외 출처 lot 제외) → 회원의 첫 교환이면 held, 아니면 requested
      (월 전체 상한 검사는 reward_exchanges 행 수를 세는 대신 KST 월별 카운터 행
       reward_exchange_month_counters(month_key PK, active_count)를 FOR UPDATE로 잠가 처리.
       잠금 순서: reward_accounts → reward_point_lots → reward_exchange_month_counters → reward_exchanges.
       취소·실패 시 active_count 감소)
취소: requested/held만, 사용자 본인. allocation 역추적으로 환불(§5-3) → canceled (월 횟수 복원)
보류: 관리자. held 상태에서는 사용자 취소 가능, 관리자는 발급 또는 실패 처리
발급: 관리자가 쿠폰 번호·만료일 입력 → issued
실패: 관리자 → 전액 환불 → failed
사용 표시: 사용자 → used (되돌리기 없음)
쿠폰 번호는 DB에 암호화 저장(기존 비밀키 체계 사용, C10과 함께 보고), 응답은 본인에게만
관리자 목록에서 첫 교환 건은 "첫 교환" 표시, 회원의 최근 30일 기록 일수·사진 기록 비율을 함께 보여 준다(판단 보조, 자동 차단 없음)
```

## 6-12. 목표 진행률 · 예상 일수

| 목표 종류 | 기준 잔액 |
|---|---|
| 상품(`product:<id>`, 건강상품) | **교환 가능 포인트**(§2-1) |
| 아이템(`item:<id>`) | 총 잔액 |
| 목표 없음 | 홈 카드는 "다음 목표"로 가장 싼 미보유 구매 가능 아이템, 없으면 가장 싼 건강상품(교환 가능 포인트 기준) |

```text
남은 포인트 = max(0, 가격 − 기준 잔액)
창 길이 W = min(REWARD_ETA_WINDOW_DAYS, 가입일부터 오늘까지 일수)   # KST, 오늘 포함
최근 적립 = 창 안에 earned_at이 있는 lot 합계
           (onboarding · levelup · refund · adjust · community_legacy 제외,
            상품 목표면 교환 제외 출처도 제외)
하루 평균 = 최근 적립 / W
예상 일수 = ceil(남은 포인트 / 하루 평균)   (하루 평균 0이면 숫자 대신 "기록을 이어가면 계산돼요")
다음 레벨 예상 일수도 같은 방식(XP, 창 W, revoke 제외)
```

화면의 "약 n일"은 이 값 하나만 쓴다. 홈 카드·목표 화면·리워드 몰·지방이 방·성장 탭이 같은 함수를 쓴다(`services/reward_rules.py`).

## 6-13. 닉네임 (Stage A — 랭킹 표시는 Stage B)

| 항목 | 규칙 |
|---|---|
| 쓰임 | 주간 랭킹 표시(Stage B), 마이페이지 회원정보, 리워드 화면의 내 정보. 커뮤니티 피드·댓글은 이번 범위에서 바꾸지 않음(피드는 계속 `name`) |
| 가입 단계 설정 | 이메일·구글·카카오 가입이 성공해 로그인된 직후 **"닉네임 정하기" 단계**를 반드시 거친다(§11-11). 입력란에는 서버가 만든 추천 닉네임이 미리 채워져 있고, 그대로 두고 "이 닉네임으로 시작하기"를 누르면 추천값을 확정한다(빈 칸으로 넘길 수 없음). 저장 시 `set_via=signup`, `generated=false`(사용자가 확인했으므로), `changed_at=null` |
| 가입 단계가 끊긴 경우 | 닉네임 저장 전에 창을 닫거나 새로고침하면, 다음 로그인 때 홈 진입 전에 같은 단계를 1회 다시 띄운다. 그때도 닫으면 자동 생성 닉네임을 유지하고 기존 회원 안내 카드 규칙을 따른다 |
| 기존 회원 | 출시(`REWARD_ONBOARDING_START_AT`) 이전 가입자는 처음 `/rewards/me`·랭킹에 나타날 때 자동 생성. 홈과 마이페이지에 "랭킹에 보일 닉네임을 정해 보세요" 안내 카드를 `generated=true`이고 `prompt_dismissed_at`이 비어 있을 때만 표시. 닫으면 `prompt_dismissed_at` 기록, 다시 안 뜸 |
| 자동 생성 | 닉네임이 없는 회원이 랭킹에 처음 들어가거나 `/rewards/me`를 처음 부를 때 "형용사 + 음식 + 4자리 숫자" 형식으로 생성(예: "부지런한 당근 4821"). 가입 단계의 추천값도 같은 생성기를 쓴다(추천은 저장하지 않고, 확정할 때 다시 검사). 단어 목록은 `reward_rules.py` 상수, 중복이면 숫자를 다시 뽑아 최대 5회, 실패 시 6자리 숫자. `generated=true` |
| 마이페이지 변경 | 회원정보 화면에서 바꾼다(§11-11). `set_via=account`. 랭킹 화면의 "닉네임 바꾸기"도 같은 API·같은 창을 쓴다(`set_via=ranking`) |
| 길이·문자 | NFC 정규화 후 2~12자. 한글·영문·숫자·공백(가운데 1칸)·`_`만. 앞뒤 공백 제거 |
| 금지 | 금칙어 목록(`nickname_blocklist.txt`, 정규화 키에 부분 포함 검사), 이메일 형태(`@` 포함), 숫자만 7자 이상(전화번호 형태), 운영 사칭어("운영자", "관리자", "CaloDetect", "칼로디텍트"), 본인 `name`과 같은 값, 본인 이메일 앞부분과 같은 값 |
| 중복 | `nickname_key` UNIQUE. 다른 회원이 쓰는 닉네임 거부 |
| 변경 주기 | 직접 변경은 `REWARD_NICKNAME_CHANGE_DAYS`(30)일에 1회. `changed_at`이 null인 상태(가입 단계에서 정한 값, 자동 생성 값, 관리자 초기화 직후)에서의 **첫 직접 변경은 주기 제한 없이 허용**. 가입 직후 오타를 바로 고칠 수 있게 하기 위해서다 |
| 같은 값으로 저장 | 지금 닉네임과 정규화 키가 같으면 변경으로 보지 않는다(`changed_at` 갱신 안 함, 200 응답) |
| 관리자 초기화 | 관리자가 부적절한 닉네임을 자동 생성 닉네임으로 되돌림. 이때 사용자의 변경 주기 제한은 풀어 준다(`changed_at=null`) |
| 동시성 | UNIQUE 위반(IntegrityError)은 "이미 쓰고 있는 닉네임이에요"로 응답 |

---

# 7. 어뷰징 방지 · 로그 지표

```text
UNIQUE idem 키로 모든 지급 중복 차단
끼니당 1회, 기록 인정 기간(오늘·어제), 사진 SHA-256 재사용 차단, 3끼 간격
온보딩·커뮤니티 포인트 실물 교환 불가, 가입 14일 대기, 월 1회
첫 교환 자동 보류(운영자 확인), 월 전체 교환 상한
반응 XP 일 상한, 랭킹에서 반응·공유 XP 제외
교환 보류(관리자)
로그 지표만(자동 차단 없음): 하루 적립 상한 도달 회원 수, 사진 해시 중복 건수, 가입 14일 직후 교환 비율
```

---

# 8. 개인정보 · 표시

```text
새로 수집하는 개인정보 없음(사진 해시는 원본 대신 SHA-256만 저장)
닉네임은 사용자가 정하거나 자동 생성되는 공개 표시명. 실명·이메일과 같은 값은 거부(§6-13)
랭킹 응답에 회원 ID·name·이메일 없음, 닉네임만
쿠폰 번호는 본인 응답에만
SERVICE_CONSENT_DRAFT.md에 "포인트·XP 적립·사용 내역, 교환·쿠폰 내역, 랭킹 공개 닉네임·주간 XP" 항목 추가 초안만 작성(운영 적용은 TBD)
```

---

# 9. API

모두 로그인 필요, 변경 요청은 기존 CSRF 검사 적용. 라우터 `backend/app/rewards.py`, prefix `/rewards`.

| 메서드 | 경로 | Stage | 설명 |
|---|---|---|---|
| GET | `/rewards/me` | A | (A) 잔액, 교환 가능 포인트, 꾸미기 전용 잔액, 오늘 받은 포인트·내역, 오늘 더 받을 수 있는 행동 목록, 만료 예정, 다음 목표(§6-12), 장착 정보, 닉네임·`nickname_prompt`(가입 단계 필요 `signup` / 안내 카드 `card` / 없음 `null`). (B부터 추가) 레벨·XP·다음 레벨·예상 일수, 연속 일수·보호 가능 여부, 사용자 목표. 플래그로 꺼진 기능의 필드는 응답에 넣지 않는다 |
| GET | `/rewards/grants?meal_id=` | A | 해당 식단 저장으로 받은 보상 묶음(기록 직후 보상 패널용) |
| GET | `/rewards/ledger?cursor=` | A | 적립·사용 내역(커서 `(created_at,id)`) |
| GET | `/rewards/items` | A | 아이템 목록 + 보유·장착·구매 가능 여부·부족 포인트 |
| POST | `/rewards/items/{id}/purchase` | A | 구매. 응답: 차감액, 온보딩 사용액, 새 잔액 |
| PUT | `/rewards/equipment` | A | `{slot, item_id \| null}` |
| GET | `/rewards/growth` | B | 레벨 로드맵, 이번 주 연속 기록(요일별 상태·보너스 예정), 요일별 XP, 오늘 XP 내역(랭킹 포함 여부 표시) |
| POST | `/rewards/levelups/{id}/seen` | B | 레벨업 축하 창 확인 |
| POST | `/rewards/streak/protect` | B | 어제 보호 |
| PUT | `/rewards/goal` | B | `{ref: "item:<id>" \| "product:<id>"}` |
| GET | `/rewards/ranking` | B | §6-10 (닉네임만) |
| GET | `/rewards/nickname` | A | 내 닉네임, 자동 생성 여부, `set_via`, 다음 변경 가능일(제한 없으면 null), 가입 단계 필요 여부 |
| GET | `/rewards/nickname/suggestion` | A | 추천 닉네임 1개(저장하지 않음). "다른 추천 받기"용, 회원당 분당 `REWARD_NICKNAME_SUGGEST_PER_MIN`(10)회 |
| GET | `/rewards/nickname/check?nickname=` | A | 저장 없이 §6-13 검사만. `{ok, reason}` — `reason`: `length` `chars` `blocked` `taken` `same_as_name` `same_as_email` `cooldown`. 회원당 분당 `REWARD_NICKNAME_CHECK_PER_MIN`(30)회, 초과 시 429 |
| PUT | `/rewards/nickname` | A | `{nickname, via: "signup" \| "account" \| "ranking"}` — §6-13 검사 후 저장. `via=signup`은 가입 단계가 아직 끝나지 않은 회원만 허용 |
| POST | `/rewards/nickname/prompt/dismiss` | A | 기존 회원 안내 카드 닫기 |
| POST | `/admin/rewards/nicknames/{user_id}/reset` | A | 자동 생성 닉네임으로 초기화 — `get_admin` |
| GET | `/rewards/products` | C | 플래그 off면 404 |
| POST | `/rewards/exchanges` | C | `{product_id}` |
| POST | `/rewards/exchanges/{id}/cancel` | C | |
| GET | `/rewards/coupons?status=` | C | `active` `pending` `closed` |
| POST | `/rewards/coupons/{id}/used` | C | |
| GET/POST | `/admin/rewards/exchanges…` | C | 목록(첫 교환 표시·기록 요약), 보류, 발급(쿠폰 번호·만료일), 실패 — `get_admin` |

오류 문구(사용자용):

```text
포인트가 부족해요. {n}P 더 모으면 돼요.
이미 가지고 있는 아이템이에요.
LV.{n}에서 열려요.
실물 교환은 가입 14일 이후에 할 수 있어요.
이번 달 교환을 이미 신청했어요. 다음 달에 다시 신청할 수 있어요.
가입 보너스와 커뮤니티 포인트는 꾸미기에만 쓸 수 있어요.
발급된 쿠폰은 취소할 수 없어요.
이번 달 교환 수량이 모두 찼어요. 다음 달에 다시 신청해 주세요.
첫 교환은 운영자가 확인한 뒤 발급돼요.
닉네임은 {min}~{max}자로 정해 주세요.
쓸 수 없는 단어가 들어 있어요.
이미 쓰고 있는 닉네임이에요.
닉네임은 {날짜}부터 다시 바꿀 수 있어요.
한글·영문·숫자와 _만 쓸 수 있어요.
이름이나 이메일과 같은 닉네임은 쓸 수 없어요.
잠시 후 다시 시도해 주세요.
```

`/system/status`:

```text
available += reward_points, reward_items, reward_nickname (A), reward_growth, reward_ranking (B),
             reward_exchange (C, 플래그 on이고 월 전체 상한이 설정됐을 때만)
policy_tbd += reward_point_values, reward_missions, reward_goal_calorie_floor, reward_nickname_blocklist,
              reward_character_sheet, reward_character_name, reward_photo_capture_time,
              reward_exchange_partner, reward_exchange_global_cap, reward_abuse_detection
```

---

# 10. 시간 · 날짜

```text
모든 일·주·월 경계는 KST (Asia/Seoul). 주 = 월요일 00:00 ~ 일요일 23:59
기록 인정 기간 판정, 연속 기록, 미션, 랭킹, 월 1회 교환 모두 같은 함수(services/timezone.py) 사용
```

---

# 11. 사용자 화면

모든 화면은 기존 웹앱 안에서 반응형으로 구현한다(PC ≥1050px 사이드바, ≤760px 하단 내비). 색·글꼴은 기존 CSS 값(`#178366→#0C5B46` 헤더, `#F4F7F5` 바탕, `#193C32` 글자, `#1C4B3A` 주 버튼, Noto Sans KR)을 쓰고, 포인트는 골드(`#8A6420` 글자 / `#E9B949` 막대), XP는 녹색(`#178366`)으로 구분한다. 지방이 대사에만 손글씨(Gaegu)를 쓴다.

## 11-0. 캐릭터 에셋

- 사용자 제공 `jibang-sprites`를 `frontend/public/jibang/`에 복사(파일명 유지). 레벨→이미지 매핑은 `Jibang.jsx` 상수 1곳(`LEVEL_SPRITES`)에서 관리(교체 가능).
- **결정 전까지 `LEVEL_SPRITES`의 LV.1~5는 모두 같은 정면 이미지(`front.png`, 시안의 LV.2 몸)를 가리킨다.** 시트의 LV.1(크게 퍼져 누운 몸)·LV.3~5(점점 마른 몸) 이미지는 복사는 하되 화면에 연결하지 않는다. 레벨 차이는 레벨 전용 배경·의상·칭호와 표정·동작(CSS)으로만 표현한다. 성장 로드맵·레벨업 창·지방이 방의 레벨 썸네일도 같은 몸에 레벨 배경을 깔아 보여준다.
- 시안의 기분 표현 이미지(기쁨·하트·샐러드 등 같은 체형의 포즈)는 쓸 수 있다. LV.1의 "귀찮은 표정"처럼 출발점을 부정적으로 그리는 표정은 기본 상태로 쓰지 않는다.
- 움직임은 CSS keyframes(숨쉬기·콩콩·반짝임)로 구현하고 `prefers-reduced-motion`에서 정지. framer-motion 등 의존성 추가 금지.
- 꾸미기 아이템은 정면 이미지(`front.png`) 위에 SVG 오버레이로 그린다(좌표는 시안 2번 기준). 배경은 `background` slot 아이템의 SVG 장면 컴포넌트(시안 BG LV.1~5).

## 11-1. 홈 리워드 카드 (시안 1, 9)

- 기존 홈(날짜·달력·칼로리 링·당류·나트륨) 유지, 리워드 카드 1개 추가.
- **Stage A 구성**: 지방이(장착 아이템), 잔액·오늘 +P, 꾸미기 전용 nP(있을 때), 다음 목표 진행률(§6-12의 자동 목표), "오늘 더 받을 수 있어요" 목록, 오늘 받은 내역(접기).
- **Stage B 추가**: 연속 기록 배지, 장착 배경, 레벨·XP 막대, 사용자 목표, 예상 일수, 보호권 안내(§6-3).
- 진행률과 예상 일수는 §6-12 기준. 상품 목표는 교환 가능 포인트로 계산하므로 총 잔액과 다를 수 있다(예: 잔액 63P, 프로틴바까지 147P).

## 11-2. 기록 직후 보상 (시안 3, 13)

- 식단 저장 성공 후 `GET /rewards/grants?meal_id=`로 받은 보상이 있으면 표시. PC는 저장 결과 옆 패널, 모바일은 전체 화면.
- 배지는 **그 저장의 `reward_grant_batches` 합계**(예: 점심 +2P와 오늘의 미션 +2P가 함께면 "+4P / +20 XP")이고, 아래에 항목별 내역을 줄마다 표시한다.
- 오늘 끼니 현황(아침·점심·저녁·간식), 3끼 완료 안내, 사진/비사진 지급 차이 안내. Stage B부터 "다음 레벨까지" 추가(Stage A에서는 XP를 표시하지 않으므로 배지에도 XP 없음).
- 보상이 없을 때(어제 이전 날짜, 중복 끼니, 사진 재사용)는 패널 대신 짧은 안내 1줄("이 기록은 포인트 지급 대상이 아니에요" + 이유).

## 11-3. 첫날 꾸미기 (시안 2)

- 첫 식단 기록 후 1회: 온보딩 내역(+10·+10·+10·+끼니), 스타터 6종, 선택 시 미리보기, "NP로 OO 착용하기", 남는 포인트 안내, "나중에 할게요".

## 11-4. 레벨업 (시안 4, 14)

- 미확인 레벨업 이벤트가 있으면 다음 화면 진입 시 축하 창. 해금된 배경 썸네일, 다음 레벨 보상, "배경 바로 적용하기"(장착 후 지방이 방으로), "나중에".

## 11-5. 리워드 메뉴 (사이드바 "리워드" + 상단 탭 4개)

| 탭 | 시안 | 핵심 |
|---|---|---|
| 리워드 몰 | 5, 15 | 잔액·교환 가능 포인트·목표 배너, 꾸미기/건강상품/AI 서비스/전문 코칭 탭, 상품 카드(진행률·남은 P·예상 일수), 실물 교환 조건 패널(가입 14일 D-n, 이번 달 n/1회), 유효기간·환불 안내 |
| 지방이 방 | 11, 12 | 큰 방 미리보기, 레벨 배경 5종(보유·적용 중·잠김+필요 XP), 잠긴 배경은 미리보기만, "이 배경 적용하기" |
| 성장 · 랭킹 | 6, 16 | 레벨 로드맵(5단계·보상·필요 XP), 이번 주 연속 기록(+5P/+10P 예정 칸), 요일별 XP 막대, 오늘 XP 내역(반응·공유 XP는 "레벨에만 반영"), 주간 랭킹("이번 주 기록 XP 기준 · 반응·공유 XP 제외 · 닉네임으로만 표시돼요"), 내 순위 줄에 "닉네임 바꾸기" 버튼 → 닉네임 창(입력, 글자 수, 규칙 안내, 다음 변경 가능일, 서버 오류 문구 표시) |
| 쿠폰함 | 17, 17-1, 17-2 | Stage C 플래그 on일 때만 탭 표시. 요약(사용 가능·발급 대기·이번 달 n/1·곧 만료), 상태 탭, 쿠폰 카드 |

## 11-6. 구매 창 (시안 15 상호작용)

- 구매 가능: 미리보기(착용 모습) + 보유/사용/구매 후 잔액 + "가입 보너스 nP가 먼저 사용돼요" + 환불 불가 안내 → "NP로 구매하기" → 완료 화면("지방이 방에서 착용하기" / 보호권은 "성장 화면에서 확인").
- 부족: 필요 P·예상 일수, 건강상품은 교환 조건 안내 → "목표 리워드로 설정하기".
- 연타 방지, 처리 중 버튼 비활성, 실패 시 서버 문구 표시.

## 11-7. 실물 교환·쿠폰 (시안 15-1, 17, 17-1, 17-2) — Stage C

- 교환 확인: 조건 체크, 교환 가능 포인트·사용·잔액(온보딩 잔액 유지 안내), 받는 곳 "CaloDetect 쿠폰함(따로 입력할 정보 없음)", 발급 전 취소 가능 안내 → "NP로 교환 신청".
- 신청 완료: 신청 → 발급 중 → 쿠폰함 도착 단계, 발급 전 취소·자동 환불 안내. 첫 교환이면 "첫 교환은 운영자가 확인한 뒤 발급돼요" 표시. **알림 문구 금지** — "쿠폰함에서 확인할 수 있어요"로 쓴다.
- 쿠폰 사용 안내에 "스캔하면 자동으로 사용 완료" 류 문구 금지. 사용 처리는 사용자가 "이미 사용했어요"를 눌러야 한다고 안내.
- "바코드 이미지 저장" 버튼은 이번 범위에서 만들지 않는다. "화면 밝기 최대"는 버튼이 아닌 안내 문구로만.
- 쿠폰 상세(PC 창): 큰 바코드(쿠폰 번호로 CODE128 생성 — 라이브러리 추가가 필요하면 보고), 번호, 발급일·유효기간·사용처, 사용 방법, "휴대폰 쿠폰함에서 열기" 안내, "이미 사용했어요".
- 쿠폰 상세(모바일 전체 화면): 진녹 바탕 흰 카드, 화면 폭 바코드, 번호 복사, 유효기간 D-n, "이미 사용했어요". 화면 밝기 제어는 웹에서 불가하므로 표시 문구만.

## 11-8. 접근성

```text
버튼·링크는 실제 button/a, 아이콘 버튼 aria-label
상태 탭 role=tablist/tab, aria-selected
창은 role=dialog aria-modal, 열릴 때 첫 버튼 포커스, Esc 닫기, 닫으면 여는 버튼으로 포커스 복귀
진행률 막대에 aria-valuenow 또는 텍스트 병기
포인트 골드·XP 녹색은 글자로도 구분(P / XP 단위 표기)
움직임 prefers-reduced-motion 존중
```

## 11-9. 시안에 있으나 이번 범위에서 제외

```text
채소 포함 미션 문구(대체 미션 사용, §6-5)
"내 기록에 맞춘 추천"(당류 기준 상품 추천) — 데이터 기반 추천 동의(기획안 9장) 확정 전 미구현, 자리만 숨김
AI 서비스·전문 코칭 구매 (준비 중 표시)
홈페이지(랜딩) 리워드 소개 섹션(시안 10) — 마케팅 문구 확정 후 별도 작업
LV.5 전용 테마로 웹 홈 헤더 색 변경 — 배경만 적용, 테마는 TBD
레벨별 체형 변화 이미지 (§11-0)
바코드 이미지 저장 버튼, 화면 밝기 제어 버튼
```

## 11-10. 시안과 다르게 구현할 문구·수치 (PR 대조 표에 포함)

시안은 v2 이전 규칙으로 그려진 부분이 있다. 아래는 **지시서 기준으로 구현**하고, 대조 표에 "의도된 차이"로 적는다. 위치는 시안 PDF 내보내기(`CaloPoint 리워드 시안 v5`, 25쪽)의 **쪽 번호**다(캔버스의 화면 번호와 다를 수 있음).

| PDF 쪽 | 시안 표시 | 구현 |
|---|---|---|
| 1, 7, 9 | 프로틴바까지 137P | 교환 가능 포인트 기준 147P(§6-12) |
| 1, 5, 7, 9, 14 | 약 10일 / 약 12일 / 약 2일 / 약 7일 | 모두 §6-12 계산식 결과 |
| 3, 12 | 두 번째 사진 끼니 저장 시 +2P / +10 XP | 미션 동시 지급분 포함 합계(+4P / +20 XP)와 항목별 내역 |
| 8 | 첫 주 타임라인: 주간 미션 Day 7, Day 5 잔액 63P | 가입 주 축소 규칙에 따라 지급일·잔액이 달라질 수 있음(§6-5). 타임라인 화면은 구현 범위 아님 |
| 8 | Day 4 "채소 포함 끼니 3회" | 대체 미션(§6-5) |
| 6, 10, 15, 16, 18~20 | 레벨별로 체형이 달라지는 지방이(LV.1 누운 큰 몸 ~ LV.5 마른 몸) | 전 레벨 같은 정면 이미지 + 레벨 배경(§11-0) |
| 11 | "LV.5 전용 테마를 적용하면 웹 홈 상단 색도 바뀌어요" | 문구 삭제 |
| 11 | "지금 속도(하루 약 60 XP)면 2주 무렵" | §6-12 계산식 결과(같은 화면 계열의 15쪽 "약 10일"과 통일) |
| 15 | 오늘 XP 내역에서 반응 XP만 "레벨에만 반영" | 식단 공유 XP에도 같은 표시 |
| 15 | "닉네임으로만 표시돼요" | 그대로(§6-13) |
| 22 | "발급되면 알림을 보내요" | "쿠폰함에서 확인할 수 있어요" |
| 24 | "직원이 스캔하면 바로 사용돼요 · 사용 완료로 옮겨져요" | 사용 후 "이미 사용했어요"를 눌러 달라는 안내 |
| 24 | "바코드 이미지 저장" 버튼 | 만들지 않음 |
| 25 | "화면 밝기 최대" 버튼 | 안내 문구로만 |

## 11-11. 닉네임 화면 (Stage A — 시안 없음, 이 절 기준으로 구현)

공통 입력 컴포넌트 `NicknameField.jsx` 하나를 가입 단계·마이페이지·랭킹 창에서 같이 쓴다.

```text
입력란 + 글자 수 표시(n/12) + 규칙 안내 1줄("한글·영문·숫자, 2~12자 · 랭킹에 표시돼요")
입력 멈춘 뒤 400ms에 /rewards/nickname/check 호출 → 결과를 입력란 아래 1줄로 표시
  (사용 가능: "쓸 수 있는 닉네임이에요", 그 밖: §9 오류 문구) — aria-describedby로 입력란과 연결, aria-live="polite"
"다른 추천 받기" 버튼 → /rewards/nickname/suggestion 값으로 입력란 교체
저장 버튼은 검사 통과 전 비활성. 저장 응답 오류가 오면 검사 결과보다 서버 응답을 우선 표시
```

**① 회원가입 마지막 단계 "닉네임 정하기"**

| 항목 | 내용 |
|---|---|
| 시점 | 이메일·구글·카카오 가입 성공 직후, 홈·첫날 꾸미기(§11-3)보다 먼저. 가입 화면과 같은 카드 레이아웃의 다음 단계로 보이게 한다(진행 표시 "2/2 · 닉네임") |
| 문구 | 제목 "랭킹에서 불릴 닉네임을 정해 주세요", 보조 "나중에 마이페이지에서 바꿀 수 있어요" |
| 기본값 | 추천 닉네임이 미리 채워짐. 지방이 정면 이미지 옆 말풍선(손글씨): "반가워, {닉네임}!" — 입력값이 바뀌면 함께 바뀜 |
| 버튼 | "이 닉네임으로 시작하기"(주 버튼) 하나. 건너뛰기 버튼 없음 |
| 저장 | `PUT /rewards/nickname {via:"signup"}` 성공 → 첫날 흐름으로 이동. 실패(중복 등)면 문구 표시 후 입력 유지 |
| 기존 가입 API | 바꾸지 않는다. 가입 요청이 성공해 로그인된 뒤 이 단계를 띄운다(C13) |
| 이탈 | 이 단계에서 닫거나 새로고침 → 다음 로그인 때 1회 재표시(`/rewards/me`의 `nickname_prompt="signup"`), 그때도 닫으면 자동 생성 유지 |

**② 마이페이지 회원정보 (`AccountInfo.jsx`)**

| 항목 | 내용 |
|---|---|
| 위치 | "이름"(읽기 전용) 아래에 "닉네임" 행 추가. 2026-10-27 후속 결정으로 계정 이름·이메일은 변경할 수 없고 이름 저장 폼·`PUT /users/me`는 삭제 |
| 구분 문구 | 이름 아래: "커뮤니티 피드에 표시돼요" / 닉네임 아래: "주간 랭킹에 표시돼요" |
| 표시 | 지금 닉네임 + 자동 생성이면 "자동으로 만든 닉네임" 배지 + "닉네임 바꾸기" 버튼 |
| 바꾸기 | 버튼 → 같은 자리에서 `NicknameField`로 펼침(별도 창 아님), "저장"·"취소". `via:"account"` |
| 변경 제한 | 제한 중이면 버튼 대신 "{날짜}부터 바꿀 수 있어요" 표시. `changed_at`이 null이면 "지금은 제한 없이 한 번 바꿀 수 있어요" 안내 |
| 저장 후 | 행이 새 값으로 바뀌고 "닉네임을 바꿨어요" 상태 문구(role=status) |

**③ 기존 회원 안내 카드**

- `nickname_prompt="card"`일 때 홈 리워드 카드 위와 마이페이지 상단에 1개: "랭킹에 보일 닉네임을 정해 보세요 · 지금은 '{자동 생성 닉네임}'" + "정하기"(마이페이지 닉네임 행으로 이동·펼침) + 닫기(×, `prompt/dismiss`).
- 둘 중 한 곳에서 닫으면 두 곳 모두 사라진다.

**④ 랭킹 (Stage B)**

- 내 순위 줄의 "닉네임 바꾸기" → `NicknameDialog.jsx`(창 안에 같은 `NicknameField`), `via:"ranking"`. 저장 후 랭킹 목록 다시 조회.

---

# 12. 파일 구성

| 구분 | 파일 |
|---|---|
| NEW | `backend/app/models_rewards.py` |
| NEW | `backend/app/rewards.py` (라우터), `backend/app/admin_rewards.py` (Stage C) |
| NEW | `backend/app/services/rewards.py` (원장·지급·차감·구매·교환), `backend/app/services/reward_rules.py` (DB 독립 규칙: 날짜·연속·레벨·미션·간격) |
| NEW | `backend/migrations/versions/20261019_01_rewards.py` (A), `…_02_rewards_growth.py` (B), `…_03_rewards_exchange.py` (C) |
| NEW | `backend/scripts/seed_reward_items.py` |
| NEW | `backend/app/data/nickname_blocklist.txt` (Stage A, 최소 예시만) |
| NEW | `frontend/src/NicknameField.jsx`(공통 입력·검사·추천), `NicknameStep.jsx`(가입 마지막 단계), `NicknamePromptCard.jsx`(기존 회원 안내) — Stage A / `NicknameDialog.jsx`(랭킹 창) — Stage B |
| MODIFY | `frontend/src/AccountInfo.jsx`(닉네임 행 추가, 기존 이름 폼 불변), `main.jsx`(가입 성공 후·로그인 후 `nickname_prompt="signup"`이면 닉네임 단계 표시), `SocialLogin.jsx`·`EmailAuthForm.jsx`(가입 성공 콜백에서 닉네임 단계로 연결 — C13 결과에 따라 필요한 곳만) — Stage A |
| NEW | `backend/tests/test_rewards_points.py`, `test_rewards_growth.py`, `test_rewards_nickname.py`, `test_rewards_exchange.py`, `test_reward_rules.py` |
| NEW | `frontend/src/Rewards.jsx`(몰·방·성장·쿠폰 탭), `RewardHomeCard.jsx`, `RewardGrantPanel.jsx`, `FirstDecorate.jsx`, `LevelUpDialog.jsx`, `Jibang.jsx`(캐릭터+장착+배경), `JibangBackgrounds.jsx`(LV.1~5 장면), `CouponBarcode.jsx`, `rewards.css` |
| NEW | `frontend/public/jibang/*` (사용자 제공 스프라이트) |
| MODIFY | `backend/app/api.py` (`save_meal`에 훅 1줄, 프로필 첫 저장 훅 1줄), `services/chat_record.py` (`confirm_draft` 훅 1줄), 가입 성공 지점(`accounts.py`·`social_auth.py`·`kakao_auth.py`) 훅 1줄씩 |
| MODIFY | `backend/app/services/community.py` (Stage A: lot 미러링 / Stage B: XP 모드 분기 — 기존 지급·감점·응답 불변) |
| MODIFY | `backend/app/config.py`, `backend/app/main.py`(라우터 등록·status) |
| MODIFY | `frontend/src/main.jsx`(메뉴 "리워드", 저장 후 보상 패널), `DailyHome.jsx`(카드), `ChatRecord.jsx`(저장 후 보상 패널), `Community.jsx`(Stage B 랭킹 API 교체·반응 보상 문구), `Visuals.jsx`(메뉴 아이콘) |
| MODIFY | `streamlit/admin_qa.py` (Stage C 교환 처리, C10) |
| DOC | `README.md`, `CHANGELOG.md`, `PENDING_DECISIONS.md`, `ROADMAP.md`, `SERVICE_CONSENT_DRAFT.md`(초안 항목 추가만) |

---

# 13. 테스트

SQLite 기본, `RUN_POSTGRES_TESTS=1`이면 PostgreSQL. 시각은 고정 시계 주입(KST 경계 테스트용).

**Stage A**

| # | 검사 |
|---|---|
| 1 | 사진 끼니 +2P·+10XP, 사진 없는 끼니 +1P·+10XP, 채팅 사진 첨부 식단 +2P(C5 결과대로) |
| 2 | 같은 날 같은 끼니 두 번 저장 → 두 번째 미지급, 간식 하루 1회 |
| 3 | `meal_date` = 그저께 → 미지급·연속 미반영, 어제 → 지급 |
| 4 | 첫 식단: 온보딩 +10과 끼니 +2 동시 지급, 두 번째 식단엔 온보딩 없음 |
| 5 | 가입·목표 온보딩 각 1회, 이메일·구글·카카오 가입 모두, `REWARD_ONBOARDING_START_AT` 이전 가입자 미지급 |
| 6 | 3끼 완료: 간격 충족 시 +3, 120분 미만 간격이면 미지급, 하루 1회 |
| 7 | 같은 사진(SHA-256) 재사용 → 끼니 미지급, 다른 회원이 같은 파일 사용해도 미지급, 저장 비활성 환경은 검사 생략 |
| 8 | 보상 훅 예외 주입 → 식단은 저장되고 보상만 없음, `POST /meals` 응답 본문이 기존과 동일 |
| 9 | 시드·데모 스크립트로 만든 식단은 보상 없음 |
| 10 | 구매: 잔액 차감, 온보딩 lot 먼저 사용(만료일 순), 부족 422 문구, 중복 보유 409, 레벨 조건 미달 403 |
| 11 | 장착: 미보유 403, slot당 1개, 해제(null) |
| 12 | 만료: 유효기간 지난 lot은 잔액에서 빠지고 `expire` spend 생성, 30일 내 만료 예정 합계 |
| 13 | 커뮤니티 미러링: 반응 지급 시 `community` lot 생성, 취소 시 회수, 기존 `/community/points/me` 응답 불변, `community_legacy` 이관(잔액 0 이하 미생성) |
| 14 | `/rewards/grants?meal_id=` = 그 저장으로 생긴 지급만, 타인 식단 404 |
| 15 | idem UNIQUE: 같은 키 직접 2회 INSERT → IntegrityError, API 경로에서는 500 없이 건너뜀 |
| 16 | (PostgreSQL) 동시 구매 2건(잔액이 1건분만) → 1건 성공·1건 422, 잔액 음수 없음 |
| 17 | (PostgreSQL) 같은 끼니 동시 저장 2건 → 지급 1건 |
| 17-1 | 두 번째 사진 끼니 저장 시 끼니 +2P와 오늘의 미션 +2P가 같은 grant batch로 묶임 |
| 17-2 | 구매 차감 순서: 온보딩 → 커뮤니티 계열 → 나머지(각 만료일 순), 응답에 제외 출처 사용액 표시 |
| 17-3 | Stage A에서 XP는 `reward_xp_events`에 쌓이지만 `/rewards/me`에 레벨·XP 필드 없음 |
| 17-4 | 회수액이 잔액보다 크면 `reward_debts` 생성, 다음 적립에서 먼저 상계, 잔액 음수 없음 |
| 17-5 | 다음 목표·예상 일수: 상품 목표는 교환 가능 포인트 기준(잔액 63P·제외 10P·프로틴바 → 147P), 창 W = min(7, 가입 후 일수), 온보딩·레벨업 제외, 평균 0이면 숫자 없음 |
| 17-6 | `REWARD_ONBOARDING_START_AT` 미설정 시 가입 온보딩 미지급(목표·첫 기록 온보딩은 정상) |

**Stage B**

| # | 검사 |
|---|---|
| 18 | 연속 3일째 +5P·+20XP, 7일째 +10P·+50XP, 10·14일째 반복, 하루 빠지면 0부터 |
| 19 | 보호권: 어제 보호 후 연속 유지, 월 2회 초과 거부, 보호된 날 끼니 보상 없음 |
| 20 | 레벨업: 300 XP에서 LV.2·bg_lv2 지급, LV.3에서 +50P·의상·배경, 동시 2단계 상승, XP 회수 후에도 레벨 유지, 레벨 포인트 1회 |
| 21 | 영양 균형 XP: 목표 ±15%·당류·나트륨 기준 이내일 때만, 목표 미설정이면 미지급, **목표보다 크게 적게 먹은 날 미지급**(범위 밖) |
| 22 | 미션: 사진 2끼 → +2P·+10XP, 주 5일 기록 → +15P, 월 20일 → +30P, 각 1회 |
| 23 | XP 모드 on: 반응 받기 XP 5/10, 일 상한 50, 누르기 일 20, 반응 포인트 0, 공유 +1P·+10XP 하루 1회 |
| 24 | 랭킹: 반응·공유 XP 제외, 동점 동순위, 주 경계(KST 월요일 00:00), 회원 ID 없음 |
| 25 | 레벨 전용 아이템 구매 시도 403, 배경 장착·해제 |
| 26 | 목표 설정: 존재하는 item/product만, `/rewards/me`의 목표 진행률·예상 일수(§6-12 기준 잔액) |
| 26-1 | 보호권: 오늘 기록 후 어제 보호 → 연속 일수 재계산, 보너스 대상이면 오늘 키로 1회 지급, 보유 0이면 거부, 수량 차감과 보호 기록이 함께 커밋 |
| 26-2 | 주간 미션 가입 주 축소: 금요일 가입 → 그 주 3일 기록으로 지급, 다음 주부터 5일 |
| 26-3 | Stage B 첫 실행 시 기존 XP로 레벨 계산·레벨 보상 1회, 미확인 레벨업 이벤트는 가장 높은 레벨 1건 |
| 26-4 | 캐릭터: `LEVEL_SPRITES` LV.1~5가 같은 정면 이미지(프런트 단위 검사 또는 빌드 확인) |
| 26-5 | 랭킹 응답 필드가 `rank`·`nickname`·`xp`·`is_me`뿐, `name`·이메일·ID 없음, 이번 주 XP 0 회원 제외 |

**Stage A — 닉네임** (N1~N8은 v2에서 Stage B였던 항목, 랭킹 관련 부분은 Stage B PR에서 다시 확인)

| # | 검사 |
|---|---|
| N1 | 닉네임 없는 회원이 랭킹·`/rewards/me`에 처음 나타날 때 자동 생성(형식·`generated=true`), 같은 회원에 두 번 생성 안 됨 |
| N2 | 길이(1자·13자 거부, 2·12자 허용), 허용 문자 외 거부, 앞뒤 공백 제거, NFC 정규화 |
| N3 | 금칙어 부분 포함 거부, 이메일 형태·숫자 7자 이상·운영 사칭어 거부, 본인 `name`·이메일 앞부분과 같은 값 거부 |
| N4 | 대소문자·공백만 다른 닉네임은 중복으로 거부(`nickname_key`) |
| N5 | 변경 주기: 자동 생성 → 첫 변경 허용, 이후 30일 내 재변경 거부(다음 가능일 문구), 관리자 초기화 후 즉시 변경 가능 |
| N6 | 관리자 초기화: 비관리자 403, 초기화 후 `generated=true` |
| N7 | (PostgreSQL) 같은 닉네임 동시 요청 2건 → 1건만 성공, 다른 1건은 중복 문구(500 아님) |
| N8 | 로그에 닉네임 문자열 없음 |
| N9 | 신규 가입자(이메일·구글·카카오 각각)의 `/rewards/me`가 `nickname_prompt="signup"`, `via=signup` 저장 후 `null`. 저장 값은 `generated=false`·`set_via=signup`·`changed_at=null` |
| N10 | 가입 단계 완료 회원이 `via=signup`으로 다시 저장하면 거부(409), `via=account`는 허용 |
| N11 | 가입 단계에서 정한 닉네임을 마이페이지에서 바로 1회 변경 가능(주기 제한 없음), 그 뒤 30일 안의 두 번째 변경은 거부 |
| N12 | 지금 닉네임과 정규화 키가 같은 값으로 저장 → 200, `changed_at` 불변 |
| N13 | 기존 회원(출시 전 가입): 자동 생성 후 `nickname_prompt="card"`, `prompt/dismiss` 후 `null`, 다시 안 뜸 |
| N14 | `/rewards/nickname/check`: 각 `reason` 값이 §6-13 규칙대로, 저장(쓰기) 없음, 분당 한도 초과 429 |
| N15 | `/rewards/nickname/suggestion`: 형식·중복 없음·저장 안 함, 분당 한도 초과 429 |
| N16 | 기존 `POST /auth/signup`(및 소셜 가입 완료)·`GET /users/me`의 요청·응답 본문이 이전과 동일(회귀). `PUT /users/me`는 2026-10-27 후속 결정으로 삭제되어 405 |

**Stage C**

| # | 검사 |
|---|---|
| 27 | 플래그 off → 모든 교환·쿠폰 API 404, 쿠폰함 탭 미표시 |
| 28 | 가입 13일째 거부, 14일째 허용(KST 날짜) |
| 29 | 교환 제외 출처 차감 금지: 온보딩·`community`·`community_legacy` lot은 교환에 쓰이지 않음, 교환 가능 포인트 부족 시 거부, 교환 후 제외 출처 잔액 그대로. `refund` lot이 원래 제한을 이어받음 |
| 29-1 | 첫 교환 자동 `held`, 두 번째 교환 `requested` |
| 29-2 | 월 전체 상한: 상한 도달 시 거부, 취소·실패 시 카운터 감소 후 신청 가능. 상한 미설정·0이면 플래그 on이어도 교환 API 404 |
| 30 | 월 1회: 두 번째 신청 거부, 첫 신청 취소 후 같은 달 재신청 허용 |
| 31 | 취소: requested·held만, issued 이후 거부, allocation 역추적 환불(만료된 lot은 새 refund lot) |
| 32 | 관리자 발급·실패·보류, 비관리자 403, 실패 시 전액 환불 |
| 33 | 쿠폰 번호: 본인 응답에만, 로그·랭킹·커뮤니티에 없음, DB 평문 아님 |
| 34 | (PostgreSQL) 같은 회원 동시 교환 신청 2건 → 1건만 성공 |
| 34-1 | (PostgreSQL) 서로 다른 회원이 상한 직전에 동시 신청 → 상한을 넘지 않음 |

**수동 확인**

| # | 검사 |
|---|---|
| 35 | 1400px·390px: 홈 카드, 기록 직후 패널, 첫날 꾸미기, 레벨업 창, 리워드 4탭, 구매 창, (C) 쿠폰 상세 |
| 36 | `prefers-reduced-motion`에서 캐릭터 움직임 정지 |
| 37 | 키보드만으로 구매 창 열기→구매→닫기, Esc, 포커스 복귀 |
| 38 | 연속 기록이 끊긴 날 화면에 부정 문구 없음 |
| 39 | 레벨 로드맵·레벨업 창·지방이 방·랜딩 제외 화면 어디에도 체형이 다른 레벨 이미지가 나오지 않음 |
| 40 | 닉네임 창: 키보드로 열기→입력→저장→닫기, 오류 문구가 입력란과 연결(`aria-describedby`) |
| 40-1 | 가입 3종 각각: 가입 직후 "닉네임 정하기" 단계가 첫날 꾸미기보다 먼저 나옴, 추천값 그대로 확정 가능, "다른 추천 받기", 중복 입력 시 문구, 새로고침 후 재로그인 시 1회 재표시 |
| 40-2 | 마이페이지: 이름·닉네임 구분 문구, 닉네임 펼침 수정·취소, 제한 중 날짜 표시, 저장 후 상태 문구. 이름·이메일은 읽기 전용(2026-10-27 후속 결정) |
| 40-3 | 기존 회원 안내 카드: 홈·마이페이지 표시, 한 곳에서 닫으면 둘 다 사라짐, 390px에서 줄바꿈 깨짐 없음 |
| 41 | §11-10 문구(알림·자동 사용·밝기·LV.5 테마)가 화면에 없음 |

기존 전체 테스트가 회귀 없이 통과해야 한다.

---

# 14. 로그

```text
reward granted {source} (금액만, 회원·식단 ID 제외)
reward grant skipped {reason: date_window|duplicate_meal|photo_reused|idem}
reward grant failed
reward purchase {item_id} / reward purchase rejected {reason}
reward level up {level}
reward points expired (합계만)
reward exchange {requested|canceled|held|issued|failed|used} (상품 ID·포인트만, 첫 교환 여부)
reward exchange rejected {reason: global_cap|monthly|account_days|insufficient}
reward exchange disabled: global cap not set (시작 시 1회)
reward nickname {generated|changed|rejected:{reason}|admin_reset} (닉네임 문자열 제외)
reward streak protected
지표: daily_cap_reached_count, photo_hash_duplicate_count, exchange_within_15d_ratio
```

이메일·이름·닉네임·쿠폰 번호·사진 경로·회원 ID는 로그에 남기지 않는다.

---

# 15. 완료 기준

```text
§0 C1~C13 확인 결과 보고, 차단 항목 없음
Stage마다: alembic upgrade head 성공(단일 head), downgrade 시 해당 Stage의 새 테이블만 제거
backend 전체 pytest 통과, frontend npm run build 성공
로컬 시나리오(Stage A): 신규 가입(이메일·구글·카카오 중 1개 이상) → 닉네임 정하기(추천값 확정 1회, 직접 입력 1회) → 목표 설정 → 사진 기록 → 첫날 꾸미기(32P → 모자 구매 → 12P) → 홈 카드 반영 → 마이페이지에서 닉네임 1회 변경 → 30일 제한 문구 확인
로컬 시나리오(Stage A, 기존 회원): 출시 전 가입 계정으로 로그인 → 자동 생성 닉네임 → 안내 카드 → 마이페이지에서 변경 → 카드 사라짐
로컬 시나리오(Stage B): 고정 시계로 5일 연속 기록 → LV.2 레벨업 창(같은 정면 이미지 + 새싹 정원 배경) → 배경 적용 → 성장·랭킹 탭 수치가 §6 규칙으로 계산됨 → 랭킹에 가입 때 정한 닉네임 표시 → 랭킹 창에서 닉네임 변경(30일 제한 적용) → 랭킹 반영
로컬 시나리오(Stage C, 플래그 on·월 전체 상한 설정): 가입 16일 → 프로틴바 교환 신청(첫 교환 → 보류) → 관리자 발급 → 쿠폰함 → 사용 표시 / 별도로 신청 → 취소 → 환불·월 횟수 복원
1400px / 390px 화면 확인, 시안 대조 표(§11-10의 의도된 차이 포함)를 PR에 첨부
PostgreSQL 동시성 테스트(#16, #17, #34, #34-1, N7) 통과, 미실행 시 "미검증" 표기
기존 가입·회원정보 API 회귀 없음(N16)
CHANGELOG에 사용자 승인일(2026-10-19)·범위·Stage·검증 결과 기록
PENDING_DECISIONS에 §3 TBD 표 추가(본인인증 제외 결정과 대체 장치 3종, 랭킹 닉네임 결정, 캐릭터 시트 충돌·캐릭터 이름, 앨범 사진, 월 전체 상한 값 포함)
ROADMAP의 Backlog에서 해당 항목 이동 기록
```

---

# 16. Codex에 전달할 명령

> `AGENTS.md`와 `docs/rules/README.md` 순서대로 규칙을 읽은 뒤, 본 보충 업무지시서(`CaloDetect_Codex_리워드_업무지시서_20261019_v3.md`)에 따라 CaloPoint·Growth·Reward 기능을 Stage A → B → C 순서로, Stage마다 별도 feature branch·PR로 구현하라. 먼저 §0의 C1~C13을 확인해 근거(파일·줄 번호)와 함께 보고하고, 차단 항목이 있으면 그 항목에 의존하는 작업은 멈춰라. Master Spec 원문과 기존 테이블·API 응답은 바꾸지 말고, 새 테이블과 `/rewards` 라우터만 추가하라. 기존 식단 생성 경로(`POST /meals`, 채팅 기록 확정)와 가입·목표 저장 지점에는 보상 훅 호출 1줄만 넣고, 훅은 SAVEPOINT 안에서 실행해 실패해도 식단 저장이 성공하게 하라. 포인트는 적립 건별 원장(`reward_point_lots`)과 차감 배분(`reward_point_allocations`)으로만 관리하고, 차감은 `reward_accounts` 행을 먼저 FOR UPDATE로 잠근 뒤 만료일이 빠른 적립 건부터 하라. 모든 지급은 `(user_id, idem_key)` UNIQUE로 중복을 막아라. 온보딩·커뮤니티 포인트는 꾸미기·보호권에만 쓰고 실물 교환 차감에서 제외하며, 꾸미기·보호권 구매에서는 이 포인트를 먼저 써라. XP는 Stage A부터 원장에 쌓되 화면 표시는 Stage B부터 하라. 목표 진행률과 예상 일수는 §6-12의 기준 잔액과 계산식 하나로만 계산하라. 끼니당 1회, 오늘·어제 날짜만 지급, 같은 사진(SHA-256) 재사용 미지급, 3끼 완료 간격 규칙을 지켜라. 체중은 어떤 보상 조건에도 쓰지 말고, 영양 균형 XP는 목표 ±15% 범위 안에서만 지급하라. 커뮤니티는 Stage A에서 기존 지급·감점을 유지하면서 같은 트랜잭션에 lot을 미러링하고, Stage B에서 `REWARD_COMMUNITY_XP_MODE`로 반응 보상을 XP로 전환하라. 주간 랭킹은 반응·공유 XP를 제외한 건강 행동 XP로 계산하고, 응답과 화면에는 닉네임만 넣어라(회원 ID·name·이메일 금지). 닉네임은 Stage A에서 새 테이블 `reward_nicknames`에 두고 §6-13의 자동 생성·검사·변경 주기·관리자 초기화 규칙을 따르라. 이메일·구글·카카오 가입이 성공해 로그인된 직후 §11-11의 "닉네임 정하기" 단계(추천 닉네임 미리 채움, 건너뛰기 없음)를 띄우고, 마이페이지 회원정보에는 기존 이름 폼을 그대로 둔 채 닉네임 행(이름은 피드, 닉네임은 랭킹에 표시된다는 구분 문구 포함)을 추가하라. 기존 가입·회원정보 API의 요청·응답은 바꾸지 말고 `/rewards/nickname` API만 사용하라. 가입 단계에서 정한 닉네임의 첫 직접 변경은 주기 제한 없이 허용하라. 커뮤니티 피드는 바꾸지 마라. 보호권은 오늘 기록한 뒤에도 어제를 보호할 수 있게 하라. Stage C(실물 교환·쿠폰함)는 `REWARD_EXCHANGE_ENABLED=false` 기본값으로 두고, 조건은 가입 14일 이후 + KST 월 1회이며, 본인인증 대신 첫 교환 자동 보류와 월 전체 교환 상한(미설정이면 교환 꺼짐)을 적용하라. 본인인증·휴대폰 번호·주소는 수집하지 마라. 쿠폰 번호는 암호화 저장하고 본인 응답에만 포함하라. 화면은 디자인 시안(§11)을 기준으로 기존 CSS 값과 사용자 제공 지방이 스프라이트로 구현하되, 레벨별 체형 변화 이미지는 쓰지 말고 모든 레벨에 같은 정면 이미지와 레벨 배경을 써라. §11-10의 시안과 다른 문구·수치는 지시서 기준으로 구현하라. 움직임은 CSS로만 하며 reduced-motion을 존중하라. 레벨 이름은 기획안 이름을 쓰고 시트의 "예뻐지는"·"가벼워진 몸" 문구는 쓰지 마라. 모든 수치는 설정값으로 두고 §3의 TBD는 임의로 확정하지 마라. §13 테스트와 §15 완료 기준을 통과한 뒤 PR을 올려라.
