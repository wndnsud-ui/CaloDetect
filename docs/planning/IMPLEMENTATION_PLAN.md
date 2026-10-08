# 구현 계획 — 2026-10-02

## 현황 및 자산 분류

| 기능/자산 | 현재 상태 | 분류 | 담당 | 우선순위 |
|---|---|---|---|---|
| best.pt | 실제 YAML 메타데이터 yolo26m.yaml / m, 150 클래스 | REUSE / DO NOT TOUCH | B | P0 |
| data.yaml, 기존 CSV | 150 클래스 일치, 기준량 unit 보유 | REUSE / DO NOT TOUCH | B | P0 |
| 음식명 연결·영양 계산 | class_id/food_name 조회, 배율 계산 | REUSE | B | P0 |
| app.py | Streamlit 분석·보정·가상 기록·대시보드 | 보존, 관리자 QA 전환은 추후 MODIFY | B | P0 |
| 회원/프로필 | 없음 | NEW | A | P0 |
| DB/API | 없음 | NEW | A | P0 |
| 사용자 화면 | Streamlit만 존재 | React NEW | C | P0 |
| 영구 식단·Correction QA | 없음 | NEW | A/B | P0 |
| 추천 후보/출처 | 기존 CSV 영양값은 존재, 추천 출처 최종 승인 TBD | 검토 | B | P0 |

## 실행 검증

기존 코드 문법, pip check, 모델/YAML/CSV 검증 통과. AppTest 초기 화면·대시보드·가상 생성/삭제 및 빈 이미지 CPU 추론 통과. 실제 음식 사진 업로드→보정→등록 전체 시나리오는 미검증이며 이를 완료로 표기하지 않는다.

## 현재 단계

React 회원/프로필/사진/식단/추천 UI, FastAPI P0 API, PostgreSQL 모델·migration·음식 적재, 기존 YOLO worker, Correction·동의·관리자 QA를 통합했다. 기존 app.py/모델/데이터는 보존한다. 가입 연령·동의 문구·이미지·추천 출처 정책 활성화는 팀 승인 대기다. 미정 탄단지 목표·당류/나트륨·끼니 적합성 점수는 계산하지 않는다.

## 순서와 범위

1. 문서/기존 자산 분석 → 신규 프로젝트 기반.
2. Auth → Profile → DB/Alembic → API schema → Meal Persistence.
3. YOLO integration → Nutrition → Today Analytics → 추천 데이터 → 추천엔진.
4. React integration → Correction → Streamlit QA.

각 단계 구현→테스트→오류 수정→기능 단위 커밋. main에 대규모 변경 커밋/푸시하지 않는다. 이번 작업은 로컬 변경으로 제공.

P1: OAuth, LLM, 재학습, 모델 registry, 운동 추천. Backlog는 ROADMAP.md 참조.

## 정책 결정 표

| 항목 | 상태 |
|---|---|
| 영양 기준 CSV | 사용자 승인: 기존 CaloDetect_nutrition_all_matched.csv 사용. 원문 Spec 보존 |
| 이미지 보관 기간 | TBD. 사용자 후속 답변에 따라 1년을 확정값으로 적용하지 않고 추후 확인 |
| 인증 상세 | 사용자 승인: 이메일/비밀번호 + HttpOnly 세션 쿠키 |
| AGE_MIN, 필수·선택 동의 문구, 이미지 위치 | TBD |
| 추천 출처, 가중치, 최근 N, P0 필터 | TBD. 개발 기본값 적용 시점은 Week 1 종료 이후 |
| 탄단지 목표, 당류/나트륨 기준 | TBD |
| 동의 문구, APPROVED 철회 정책 | TBD |
| LLM 공급자, 배포 대상, 재학습 N | TBD / P1 |

## 테스트/리스크

목표 공식·범위·상한, 0/음수/NaN 섭취량, 기존 CSV 150클래스, KST 날짜 경계, API validation/error shape, Frontend production build 검증. 이후 Auth 사용자 분리·재로그인 영구화·다중 detection 관계·동의 철회·QA 403을 추가한다.
현재 Postgres 실행 여부와 운영 배포 환경은 별도 검증 필요. 신규 웹 기반이 완성된 P0 서비스처럼 보이지 않도록 준비 상태를 명시한다.

## 기반 구현 검사 결과

2026-10-02: pytest 9 passed, React production build 성공, Backend pip check 성공. 원본 app.py/모델/YAML/CSV의 Git diff 없음. 실제 DB 연결·브라우저 화면·완성 회원 흐름은 미검증.

## P0 통합 검사 결과

UI/회원 추가 검사: Backend 22 passed, 1 skipped. 격리 PostgreSQL + 실제 YOLO smoke 7 passed. Edge PC/모바일에서 음식/목표 계산, 가입, 목표 저장, 이름 수정, 세션 유지, 재로그인 복원, JS 오류/가로 넘침 검증 완료. [화면과 검증 상세](../UI_VALIDATION.md). 서비스 가입 연령과 동의 문구는 여전히 사용자 전달 대기다.

기존+회원+서비스 테스트 19 passed. 별도 PostgreSQL test schema에서 가입→프로필→저장→재로그인 유지, 데이터 분리/원자 저장, 다중 detection/Correction/QA/철회, 추천3개/acted, 잘못된 이미지/CSRF/연령, 실제 YOLO 빈 이미지 업로드 등 6 passed. PostgreSQL migration/seed 적용 성공. 브라우저 회원가입 폼·목표 계산, JS 오류 없음 확인. 실제 음식 인식 정확도/전체 UI 시나리오는 추가 검수 대상이다. 테스트용 정책은 운영 설정과 분리했다.
