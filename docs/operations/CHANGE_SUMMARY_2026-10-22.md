# 2026-10-22 변경 사항 정리

## 변경 내용 요약

- **지방이 꾸미기 개선:** 운동복·전용 의상·코스튬을 실제로 입은 레벨별 이미지로 교체하고, 안경과 모자를 얼굴 위치·각도에 맞춰 정렬했다.
- **모바일 홈 개선:** 날짜와 주간 달력 잘림을 수정하고, 로그인 / 회원가입 버튼을 눈에 보이게 배치했다.
- **캐릭터 표시 개선:** 홈 지방이를 확대하고 머리·모자가 잘리지 않도록 방 영역과 위쪽 여백을 늘렸다.
- **건강 리워드 가독성 개선:** 작은 안내 글씨를 키우고 색 대비를 높였으며, 모바일 보상 수치를 별도 행으로 배치했다.
- **식단 기록 → 커뮤니티 연결:** 보상 화면에 ‘커뮤니티에 남기기’를 추가해 방금 저장한 식단이 선택된 공유 창으로 연결했다.
- **사진 찍기 개선:** 음식 추가와 채팅 모두 실시간 카메라를 사용하도록 변경했다. 모바일 후면 카메라를 우선 요청하며, 사진 선택은 별도 버튼으로 유지한다.

작성 기준: 현재 `feature/rewards` 브랜치의 미커밋 변경 사항과 이번 작업 기록. 아래 내용은 2026-10-22 작업 범위이며, 이전에 반영한 10월 21일 변경 전체를 다시 나열하지 않는다. 이 문서 작성으로 커밋·원격 업로드를 수행하지 않았다.

## 파일별 변경 내용

### 캐릭터·의상

| 파일 | 변경 내용 |
|---|---|
| [frontend/src/Jibang.jsx](../../frontend/src/Jibang.jsx) | 의상 착용 이미지를 공용 캐릭터에 연결. 의상 해제 시 원본 몸을 표시한다. 원본 레벨별 눈 좌표를 보정하고, 안경의 중심·배율·회전을 양쪽 눈 기준으로 계산한다. 모자·머리 장식도 얼굴 각도와 의상별 정수리 위치를 사용한다. 안경 테두리·연결부를 정리했다. |
| [frontend/src/jibangClothing.js](../../frontend/src/jibangClothing.js) **신규** | 의상별 이미지 경로, 지원 레벨, 이미지별 눈·정수리 좌표를 관리한다. outfit 슬롯 의상을 우선 선택하고, 미리보기에서 해당 레벨 이미지가 없으면 지원 변형을 선택한다. |
| [frontend/public/jibang/clothing/](../../frontend/public/jibang/clothing/) **신규** | 투명 배경 의상 이미지 11개 추가. 아래 목록 참고. |
| [frontend/src/Rewards.jsx](../../frontend/src/Rewards.jsx) | 몰에서 운동복을 미리 볼 때 기존 outfit 의상이 미리보기를 가리지 않도록 표시용 장비를 정리한다. |
| [backend/app/services/rewards.py](../../backend/app/services/rewards.py) | 장착 시 리워드 계정을 잠그고, 운동복(prop)과 전용 의상(outfit)이 동시에 겹치지 않도록 이전 몸통 의상만 해제한다. 소유권과 물병 같은 일반 소품은 유지한다. |
| [backend/tests/test_rewards_points.py](../../backend/tests/test_rewards_points.py) | 운동복↔전용 의상 전환, 미보유 아이템 장착 실패 시 기존 옷 유지, 소유권·일반 소품 유지 검증 추가. |

추가 이미지:

- `workout-front.png`, `workout-lv1.png` ~ `workout-lv5.png`: 운동복 정면·LV.1~5.
- `sailor-lv3.png` ~ `sailor-lv5.png`: 전용 의상 LV.3~5.
- `garden-lv4.png`, `garden-lv5.png`: 멜빵 코스튬 LV.4~5.

### 모바일 홈·리워드 표시

| 파일 | 변경 내용 |
|---|---|
| [frontend/src/DailyHome.jsx](../../frontend/src/DailyHome.jsx) | 날짜 제목과 오늘 배지를 구분하고, 계정 버튼을 제목 바깥으로 이동했다. 비회원은 ‘로그인 / 회원가입’, 회원은 ‘내 계정’을 표시한다. 홈 안내 캐릭터의 figureWidth를 118에서 170으로 확대했다. |
| [frontend/src/dashboard.css](../../frontend/src/dashboard.css) | 홈 헤더에 적용되던 공통 가로 flex 배치를 해제해 날짜 아래에 주간 달력을 배치한다. 7일 칸의 최소 너비와 줄바꿈을 조정했다. 로그인 버튼 스타일을 추가하고, 지방이 방 영역을 최종 240×300px로 확대했다(가용 너비에 따라 축소). |
| [frontend/src/rewards.css](../../frontend/src/rewards.css) | 홈 리워드의 XP·목표·보상 글씨를 13~17px로 확대하고 보조 글자 색을 진하게 조정했다. 모바일에서 보상 수치를 설명 아래 행으로 배치한다. |

### 식단 기록 후 커뮤니티 공유

| 파일 | 변경 내용 |
|---|---|
| [frontend/src/RewardGrantPanel.jsx](../../frontend/src/RewardGrantPanel.jsx) | 기록 직후 보상 패널에 ‘커뮤니티에 남기기’ 버튼과 onShare 콜백을 추가했다. 기존 ‘홈에서 오늘 기록 보기’ 버튼도 유지한다. |
| [frontend/src/main.jsx](../../frontend/src/main.jsx) | 공유할 식단 ID를 상태로 보관한다. 공유 버튼을 누르면 보상 패널을 닫고 커뮤니티로 이동해 해당 ID를 전달한다. 공유 창 진입 요청을 소비하면 상태를 비운다. |
| [frontend/src/Community.jsx](../../frontend/src/Community.jsx) | 전달된 식단 ID로 공유 폼을 자동으로 열고, 공유 가능 목록의 meal_id와 대조해 해당 식단을 선택한다. 이미 공유했거나 공유할 수 없는 식단이면 안내한다. |

사용 흐름: **식단 저장 → 보상 패널 → 커뮤니티에 남기기 → 이야기 작성·사진 공개 여부 확인 → 공유하기**.

버튼을 누르는 것만으로 게시하지 않는다. 사진 공개는 기본 미동의이며 기존 공유 폼의 선택 동의를 따른다. 추가 버튼은 현재 보상 항목이 표시되는 패널에 적용했으며, 보상 없는 기록의 간단 안내에는 추가하지 않았다.

### 카메라 촬영

| 파일 | 변경 내용 |
|---|---|
| [frontend/src/PhotoInput.jsx](../../frontend/src/PhotoInput.jsx) | 모바일 사용자 에이전트를 검사해 capture 파일 입력으로 보내던 분기를 제거했다. 모바일·PC 모두 getUserMedia로 실시간 미리보기와 촬영을 제공한다. 기존 촬영 취소·화면 종료 시 카메라 트랙 정리를 유지한다. |
| [frontend/src/ChatRecord.jsx](../../frontend/src/ChatRecord.jsx) | 터치 기기를 파일 선택창으로 보내던 분기를 제거했다. 후면 카메라 우선 요청으로 변경하고, 카메라 실패 후 앨범이 자동으로 열리던 동작을 제거했다. 지원하지 않는 접속 환경은 안내 문구를 표시한다. |

실시간 카메라는 브라우저 권한과 HTTPS 또는 localhost가 필요하다. 휴대폰에서 PC의 일반 HTTP IP 주소로 접속하면 제한될 수 있다. 이번 변경에 HTTPS 배포 설정은 포함하지 않았다.

### 문서

| 파일 | 변경 내용 |
|---|---|
| [CHANGELOG.md](../../CHANGELOG.md) | 10월 22일 의상·안경·모자·모바일 홈·리워드 가독성·공유 연결·카메라 변경과 관련 검증 기록을 추가했다. |
| [docs/rules/CURRENT_IMPLEMENTATION.md](../rules/CURRENT_IMPLEMENTATION.md) | 투명 착용 이미지와 의상 간 장착 처리 기준을 추가했다. |
| [docs/design/JIBANG_CLOTHING_ASSETS.md](../design/JIBANG_CLOTHING_ASSETS.md) **신규** | 의상 이미지 제작 방법·입력 원본·프롬프트·표시 기준을 기록했다. |
| [docs/operations/CHANGE_SUMMARY_2026-10-22.md](CHANGE_SUMMARY_2026-10-22.md) **신규** | 이번 변경의 요약, 파일별 수정 사항, 검증 범위와 남은 확인 사항을 정리한 현재 문서. |

`docs/operations/TEAM_LOCAL_TEST_GUIDE.md`는 IDE에서 열려 있지만 현재 작업의 변경 파일에는 포함되지 않는다. Master Spec 원문은 변경하지 않았다.

## 검증 결과와 남은 확인

- GitHub PR 준비 시 재검사: Frontend production build·Node 12개 통과, Backend `test_rewards_points.py` 21개 통과·PostgreSQL 전용 1개 제외(Stage A 커뮤니티 포인트 설정을 테스트 프로세스에 명시).

- 최신 카메라 변경까지 Frontend production build 성공, 기존 Node 테스트 12개 통과, `git diff --check` 통과. 이 테스트 12개가 모든 신규 UI 동작을 검증하는 것은 아니다.
- 의상 작업 당시 기록: 장착 회귀 2개 및 관련 Backend 29개 통과·PostgreSQL 전용 1개 제외. Stage A 설정을 테스트 프로세스에 명시한 결과이며, 이번 문서 작성 중 재실행하지 않았다.
- 의상·안경의 초기 브라우저 확인 기록은 CHANGELOG에 있다. 이후 모자·모바일 배치·글자 크기·상단 여백의 최종 화면, 저장 직후 공유 연결, 휴대폰 실카메라 촬영은 추가 수동 확인이 필요하다.
- 프런트엔드 서버가 꺼져 있던 문제는 재실행했다. 당시 화면·API·그래프 서버의 HTTP 200 응답을 확인했으며, 이는 현재 모든 기능의 통합 검증 완료를 의미하지 않는다.

## 변경에서 제외한 로컬 자료

- `표정 변화jibang-motion-sheet.zip`: 현재 미추적 원본 참고 자료. 서비스 코드 변경에 포함하지 않는다.
- `.runtime-logs/`와 임시 빌드 결과: 로컬 실행·검증 자료. 팀에 공유할 소스 목록에서 제외한다.
- 개인 `.env`, DB, 사용자 사진·로그·비밀키 및 원본 모델·CSV·YAML은 이번 변경 대상이 아니다.
