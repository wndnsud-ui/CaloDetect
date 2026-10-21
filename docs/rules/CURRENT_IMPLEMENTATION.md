# 현재 구현 기준

기준일: 2026-10-20. 코드 기준: `ed87d68`(리워드 기능 추가, origin/develop 반영). 이후 코드·사용자 결정이 달라지면 근거를 확인하고 이 문서를 갱신한다. 구현되어 있다는 사실과 운영 정책 승인을 구분한다.

## 문서 적용

사용자의 명시적 지시 → 최신 CHANGELOG 결정 → 개발 규칙·본 문서 → 해당 기능 업무지시서 → Master Spec 원문 순으로 충돌을 해소한다. 미결 정책은 PENDING_DECISIONS를 확인한다. Master Spec은 원문을 보존하고, 충돌하는 과거 지시를 다시 구현하지 않는다.

## 구현 범위와 근거

| 영역 | 현재 동작 | 주요 근거 |
|---|---|---|
| 웹·인증 | React/FastAPI. 만 18세, 이메일·Google·카카오, HttpOnly 세션. Apple 미제공. 소셜 계정 자동 연결 없음 | backend/app/accounts.py, social_auth.py, kakao_auth.py |
| 식단·사진·영양 | 기존 YOLO 모델과 CSV로 인식·계산·저장. 직접 음식 선택·음식명 수정·섭취량 지원 | backend/app/api.py, services/correction.py, frontend/src/PhotoInput.jsx |
| 분석·추천 | 목표·기록에 따른 수치 계산. Streamlit 그래프 서버 유지 | services/recommendation.py, streamlit/charts.py |
| 챗 기록 | CHAT_RECORD_ENABLED 기본 false. 활성화 환경에서 챗 식사기록·섭취량 수정 제공. LLM 서비스 없음 | backend/app/main.py, services/chat_record.py, services/consumption_record.py |
| 커뮤니티 | 식단 공유·좋아요·추천·포인트. 사진 공개는 게시물별 선택 동의. 화면 랭킹은 리워드 랭킹 | frontend/src/Community.jsx, backend/app/services/community.py |
| 리워드 A/B | 포인트 원장·XP·미션·연속 기록·보호권·꾸미기·성장·닉네임·주간 랭킹 | backend/app/services/rewards.py, frontend/src/Rewards.jsx |
| 교환·쿠폰 C | 건강상품 신청·첫 교환 보류·관리자 발급·취소/실패 환불·쿠폰함·바코드 | services/reward_exchange.py, frontend/src/RewardExchange.jsx, CouponBarcode.jsx |
| 관리자 | React 관리자 메뉴. 교환 상태·발급·보류·실패·닉네임 검색/초기화. 서버 admin 검사 | frontend/src/AdminPage.jsx, backend/app/admin_rewards.py |
| 개발 테스트 | 로컬 개발 설정에서만 API 등록. test@calodetect.local 본인만 메뉴·화면·생성/초기화 허용 | backend/app/dev_demo.py, frontend/src/DevDemo.jsx, main.jsx |

## 후속 결정으로 바뀐 규칙

- 2026-10-21 사용자 결정: 리워드 메뉴는 몰 전용, 지방이 방·성장/랭킹·쿠폰함은 마이페이지 탭에서 제공한다. 기존 홈·구매 후·레벨업 바로가기도 마이페이지 해당 탭으로 이동한다. 쿠폰함은 교환 활성 조건을 유지한다.

- 2026-10-21 사용자 결정: 기본 꾸미기(스티커·안경·리본·모자·운동화·민트 방)와 최초 포근한 아침 방은 포인트 없이 기본 제공한다. 기존 회원도 누락 소유권을 지급하고 기존 구매 원장은 보존한다. 몰에서 바로 적용·빼기를 제공한다. 최초 포근한 아침 방이 기본 배경이며 기존 starter_bg는 깔끔한 민트 방이다.

- 재학습은 보류가 아니라 폐기다. 동의·후보 수집·관리자 재학습 API·Streamlit admin_qa.py를 제거했다. migration `20261020_01`은 관련 테이블·동의 컬럼을 삭제한다. downgrade는 빈 구조만 복원하며 삭제 데이터를 복구하지 못한다. 기존 모델 best.pt는 유지한다.
- 리워드 Stage A/B/C는 구현했다. Stage C는 기본 꺼짐이며 활성 조건을 충족할 때만 API·교환 화면이 열린다. 본인인증·전화번호·배송지 수집은 이번 범위에 없다.
- 닉네임은 대기기간 없이 계속 변경할 수 있다. 형식·중복·금칙어 검사는 유지한다. config의 기존 reward_nickname_change_days 값이 남아 있어도 next_change_at은 None을 반환한다.
- 지방이는 시트의 LV.1~5 몸과 애니메이션·장착 아이템을 사용한다. 체형 평가 문구는 사용하지 않는다. 홈 기록 안내는 배경 없는 JibangFigure를 재사용한다.
- 관리자 기능은 Streamlit이 아니라 React 웹에서 제공한다.
- 리워드 몰은 꾸미기·건강상품·전문 코칭으로 구성한다. AI 서비스 탭은 제거했다. 코칭 3종의 내용·포인트는 시안이며 신청·차감되지 않는다.
- 무료/유료 구분은 확정하지 않았다. 소개 하단 버튼은 '회원가입 후 시작해 보기'이며 회원가입으로 이동한다. 소개 네 번째 카드는 커뮤니티·리워드를 소개하고 커뮤니티로 연결한다.

## 설정과 개발 기본값

코드 설정은 backend/app/config.py, 예시는 .env.example이 기준이다. 개인 .env 값을 팀 운영 규칙으로 복사하지 않는다.

| 항목 | 코드 기본값·조건 |
|---|---|
| 리워드 | REWARD_ENABLED=true. 수치·레벨·미션은 REWARD_* 개발 기본값 |
| 신규 회원 기준 | REWARD_ONBOARDING_START_AT 미설정 시 가입 온보딩 미지급·출시 이전 회원 처리 |
| 커뮤니티 XP | 코드 기본값 false. 2026-10-21 사용자 승인으로 현재 로컬 실행 설정은 REWARD_COMMUNITY_XP_MODE=true, 기존 반응 포인트 3종은 0으로 전환. 팀원은 각자 설정·재시작 필요 |
| 교환 활성 | REWARD_EXCHANGE_ENABLED=true + 양수 월 전체 상한 + OAUTH_STATE_SECRET 필요. 비활성이면 교환 API 404 |
| 교환 조건 | 가입 14일, KST 월 1회, 첫 교환 보류가 기본. 온보딩·커뮤니티 계열 포인트 교환 제외 |
| 포인트 유효기간 | 설정 기본 365일. 화면은 12개월로 안내. 운영 표현·정책 최종 확인 필요 |
| 개발용 예외 | 로컬 교환 테스트에서 가입 일수 0 등의 설정을 사용할 수 있으나 운영 기본값을 바꾸지 않는다 |

테스트 더미는 리워드용이다. 식단 더미는 별도 스크립트다. 리워드 초기화 또는 초기화 체크 후 더미 생성은 해당 계정의 교환·쿠폰 이력도 삭제한다. 식단·닉네임은 유지한다. 첫 신청은 held(보류)로 관리자 전체/보류 목록에 나타나며 발급 후에는 issued다.

## DB·검증·운영 미결

리워드 migration은 `20261019_01` → `20261019_02` → `20261019_03`, 모델 개선 폐기는 `20261020_01`이다. 팀원 적용 전에 백업과 기존 revision을 확인한다. 이번 문서 정리에서는 DB 작업을 실행하지 않는다.

직전 업로드 검증: Backend 247통과·9제외·기존 추천 오류 응답 형식 테스트 3실패. Frontend build·Node 12통과. 현재 문서 정리는 문서 연결·차이 검사만 수행한다. Google·카카오 실계정, 운영 배포, 실제 제휴 쿠폰 검증 완료를 의미하지 않는다.

운영 동의·이미지 보관·제휴·단가·수치·운영 배포의 미확정 사항은 [결정 대기 사항](PENDING_DECISIONS.md)을 따른다.
