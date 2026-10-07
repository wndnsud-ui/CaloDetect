# 지방이 젤리 3D 개선 — 2026-10-08

사용자 요청과 첨부 개선 업무지시서의 현재 외형 보존 원칙을 적용했다. 기존 비율·얼굴 위치·아이보리/민트/라임 색상·하트 안기·회전·성장 연결을 유지한다. 문서의 라이브러리 예제·Blender 작업 방식은 참고이며 기존 Three.js 프로젝트에 맞춰 구현했다.

## 구현

- 본체 `frontend/public/models/character/jibang.glb`: 61,920 bytes, 32,400 triangles. 공유 geometry로 파일 크기를 줄여 Draco/텍스처 다운로드 없이 로딩한다.
- `models/items/ribbon.glb`, `sport.glb`, `crown.glb`를 HeadAnchor/BodyAnchor에 장착. Head/Face/Body/양손 anchor와 파츠 이름을 포함한다.
- MeshPhysicalMaterial: 몸통 roughness .24 / transmission .15 / IOR 1.45 / coat .2, 새싹 transmission .2, 민트 발 .1, 볼 .06, 눈 roughness .08. 손은 기존 크림색을 보존한다.
- 스튜디오 환경광과 key/fill/rim light, ACES tone mapping, 저농도 방사형 contact shadow. 실제 subsurface scattering 셰이더 대신 thickness·attenuation·transmission으로 가벼운 투과 느낌을 표현한다.
- 호흡·눈 깜빡임·새싹 흔들림, 포인터 얼굴 추적, 회전 damping과 손/새싹의 시차, 클릭/버튼 점프와 squash/stretch, 꾸미기 적용 시 회전.
- 기존 pause/reduced-motion·회전/정면/손 흔들기 유지. reduced-motion에서도 직접 회전 가능. 모바일 touch-action pan-y로 세로 스크롤 유지.
- DPR 제한, 작은 스타일 미리보기에서 transmission 추가 패스 생략, 화면 밖/숨겨진 탭 렌더 생략. scene·geometry·material·texture·환경맵·observer 정리, 비동기 로딩 완료 후 unmount 처리.
- GLB 로딩 실패 시 동일 형태 procedural 모델로 대체하고 안내. 홈페이지 메인 이미지 변경 없음.

## 검증과 한계

- Vite build, 기존 로그인/로그아웃·캐릭터/챌린지/메뉴판 테스트 및 새 GLB·터치·reduced-motion·로딩 실패 대체 검사 통과.
- 테스트 Chromium에서 렌더 프레임 측정 PC 및 모바일 크기 에뮬레이션 약 60 FPS. 실제 휴대폰 GPU·장시간 사용·배터리 성능은 검증하지 않았으므로 전 기기 30/60 FPS 보장을 의미하지 않는다.
- GLB에 skeletal rig 또는 baked animation/morph clip을 포함하지 않는다. 이름 있는 파츠·anchor를 런타임에서 변형한다. 별도 Blender 파일은 생성하지 않는다.
- 서버 보유 아이템·포인트 원장은 기존 미완료 상태를 유지한다.

재생성: `npm.cmd --prefix frontend run models:jibangi`. 원형/재질/아이템 source는 `frontend/src/jibangiModel.js`, export는 `frontend/scripts/build-jibangi.mjs`에서 관리한다.
