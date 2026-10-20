# 로드맵

> 2026-10-20 사용자 결정: 모델 개선(재학습)·관리자 재학습 QA·모델 개선 동의는 폐기했고 관련 API·Streamlit `admin_qa.py`·`retraining_samples` 테이블·동의 컬럼을 삭제했다. 아래 내용 중 해당 부분은 과거 기록이다.

2026-10-20 사용자 승인: 리워드 v3(CaloPoint·Growth XP·꾸미기·리워드 몰·주간 랭킹·닉네임) Stage A·B를 Backlog의 "포인트"에서 현재 범위로 이동. 실물 교환·쿠폰함(Stage C), AI·코칭 실제 제공, 현금 결제는 계속 제외. 근거: `docs/rules/CaloDetect_Codex_리워드_업무지시서_20261019_v3_AI경고문추가.md`.

2026-10-16 사용자 향후 방향: 누적 포인트를 칼로몰 및 코칭 서비스 이용에 활용한다. 현재 범위는 적립·감점·잔액·랭킹까지 유지한다. 포인트 사용·결제·코칭 연결은 후속 범위이며 교환 비율, 차감, 취소·환불, 이용 조건, 소멸 정책은 별도 확정한다. 이번 결정으로 관련 API·화면을 선행 구현하지 않는다.

2026-10-14 사용자 승인(커뮤니티 v5), 2026-10-16 실행 요청: Feed·Like·Calo Point 및 주간 랭킹을 현재 범위에 포함. 원본 식단 실시간 공유·반응 취소/삭제 감점·메타데이터 제거 사진 사본으로 제한. Follow·댓글·Coach·챌린지·포인트 사용처는 계속 제외. 실제 DB 전환 상태는 [착수 점검](COMMUNITY_V5_PREFLIGHT.md) 참조.

P0: Auth → Profile/목표 → PostgreSQL 영구 저장 → 탐지/보정/영양 → 오늘 상태/History → 출처 검증 추천 3개 → Correction/동의 → Streamlit 관리자 QA.

P1(P0 완료 후): Google OAuth, LLM 설명, 자연어 조건·what-if, 실제 재학습, registry/promote/rollback, 운동 추천, 메뉴판·웹캠.

Backlog(현재 구현 금지): 위치 매장, Health 플랫폼, Coach/소셜, 챌린지·광고·파트너십, 장보기·바코드·웰니스, 음식 매핑 고도화/외부 데이터 자동 연동.
