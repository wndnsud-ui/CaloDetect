# 리워드몰 구현 업데이트 · DB 마이그레이션 실행 가이드

대상: `develop`의 **`7f47570` — 리워드몰 구현**을 받은 팀원. Windows PowerShell 기준이며 모든 명령은 자신의 **CaloDetect 프로젝트 루트**에서 실행합니다.

## 먼저 알아둘 내용

- `git pull`은 코드만 받습니다. 각자 PC의 PostgreSQL에는 아래 DB 업데이트가 필요합니다.
- **Docker 백엔드**는 새 코드로 빌드·시작하면 마이그레이션과 시드를 자동 실행합니다.
- **로컬 Python 백엔드**는 직접 마이그레이션 → 리워드 시드 → 서버 재시작을 실행합니다.
- 기존 DB volume은 유지합니다. `docker compose down -v`, DB 초기화, 더미 초기화는 실행하지 않습니다.
- 이번 작업은 실행 안내 문서입니다. 이 문서 작성 중 DB를 변경하지 않았습니다.

## 1. 변경되는 DB 구조

| 순서 | Revision | 작업 내용 |
|---|---|---|
| 기존 기준 | `20261020_01` | 이번 마이그레이션의 부모 revision |
| 1 | `20261022_01` | 상품 하위분류·정가·옵션·최대 수량·목록 노출·콜라보 브랜드·코치 연결·콘텐츠·시연 여부 컬럼 추가. 교환 내역에 수량·선택 옵션 추가. 기존 `ai_report`, `pro_coaching` 상품 비활성화. |
| 2 | `20261022_02` | 코치 프로필·콘텐츠·이용권 테이블과 상품의 코치 외래키 추가. |

기존 교환 내역에는 `quantity=1`, `option_label=null`이 적용됩니다. 기존 회원·식단·포인트 원장을 초기화하지 않습니다. 신규 revision 파일을 만들거나 기존 migration 파일을 수정할 필요가 없습니다.

## 2. 코드 받기와 백업 — 공통

현재 수정 중인 파일은 먼저 보존하고 팀 Git 절차에 따라 정리합니다. 아래 `pull`이 실패하면 중단하고 충돌을 해결합니다. 개인 `.env`를 다른 팀원 파일로 덮어쓰지 않습니다.

```powershell
git status
git switch develop
if ($LASTEXITCODE -ne 0) { throw '브랜치 전환 실패. 현재 변경 사항을 확인하세요.' }
git pull --ff-only origin develop
if ($LASTEXITCODE -ne 0) { throw '업데이트 실패. Git 상태를 확인하세요.' }
```

Docker Desktop을 켠 뒤 DB를 시작합니다. **로컬 Python 백엔드는 실행 터미널에서 Ctrl+C로 종료**하고, Docker 백엔드는 아래처럼 중지합니다. DB는 중지하지 않습니다.

```powershell
docker compose up -d db
if ($LASTEXITCODE -ne 0) { throw 'DB 시작 실패. Docker Desktop을 확인하세요.' }
docker compose stop backend
powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\scripts\backup_local_db.ps1
if ($LASTEXITCODE -ne 0) { throw '백업 실패. 마이그레이션을 진행하지 마세요.' }
```

백업 성공 메시지와 파일 경로를 확인합니다. 기본 저장 위치는 `%LOCALAPPDATA%\CaloDetect\backups`이며 회원 데이터가 포함되므로 GitHub에 올리지 않습니다. 스크립트는 로컬 `.env`의 `POSTGRES_USER`, `POSTGRES_DB`를 사용합니다. 앱의 실제 DB와 다른 값으로 설정했다면 실행 전 연결 대상을 확인해야 합니다.

## 3-A. 백엔드도 Docker인 경우

**이 절차와 3-B 중 본인 실행 방식 하나만 사용합니다.**

```powershell
docker compose up -d --build backend
if ($LASTEXITCODE -ne 0) { throw 'Backend 빌드 또는 시작 실패' }
docker compose logs --tail 80 backend
```

시작 스크립트 `backend/scripts/start.py`가 아래 순서로 실행합니다.

1. `alembic upgrade head`
2. 음식 시드
3. 리워드 아이템·상품·코칭 시드
4. 허용된 로컬 개발 계정 준비
5. API 서버 시작

컨테이너 시작 명령 성공만으로 migration 완료를 판단하지 않습니다. 로그에서 **`Application startup complete`**를 확인하고 현재 revision을 조회합니다.

```powershell
docker compose exec backend python -m alembic -c backend/alembic.ini current
if ($LASTEXITCODE -ne 0) { throw 'Revision 확인 실패. Backend 로그를 확인하세요.' }
```

이번 배포 기준 결과는 **`20261022_02 (head)`**입니다. 이후 추가 배포를 받은 경우 더 최신 head일 수 있습니다.

## 3-B. Docker는 DB만, 백엔드는 로컬 Python인 경우

프로젝트 루트에서 실행합니다. `.venv-backend`와 `.env`가 준비되어 있어야 합니다. 준비가 안 된 PC는 [팀원 로컬 테스트 가이드](TEAM_LOCAL_TEST_GUIDE.md)를 먼저 따릅니다.

현재 DB revision을 확인한 후 이번 revision까지 적용합니다. 기존 revision이 더 오래됐다면 Alembic이 중간 migration도 순서대로 실행하므로 백업을 먼저 완료해야 합니다.

```powershell
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini current
if ($LASTEXITCODE -ne 0) { throw '현재 DB revision 조회 실패' }
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini upgrade head
if ($LASTEXITCODE -ne 0) { throw '마이그레이션 실패. 서버를 켜지 말고 오류를 확인하세요.' }
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_reward_items
if ($LASTEXITCODE -ne 0) { throw '리워드 시드 실패' }
.\.venv-backend\Scripts\python.exe -m alembic -c backend/alembic.ini current
if ($LASTEXITCODE -ne 0) { throw '적용 결과 조회 실패' }
```

**`20261022_02 (head)`**를 확인한 뒤 백엔드를 실행합니다. 이미 같은 최신 revision이라면 `upgrade head`는 적용된 migration을 다시 실행하지 않습니다.

```powershell
$env:FRONTEND_ORIGIN='http://localhost:5174'
.\.venv-backend\Scripts\python.exe -m uvicorn backend.app.main:app --reload --host ::1 --port 8000
```

`Application startup complete`를 확인합니다. 이 터미널은 열어 두고, 프런트엔드는 별도 터미널에서 [기존 실행 가이드](../../CaloDetect_로컬_실행가이드.md)대로 실행합니다.

## 4. 적용 후 확인

브라우저에서 `http://localhost:8000/health/database`를 열어 `status: ok`를 확인합니다. 웹앱 `http://localhost:5174`에서는 Ctrl+F5 후 로그인합니다.

- 리워드몰: 상품 목록·상품 상세·보유 포인트가 정상 표시되는지 확인합니다.
- 꾸미기: 전용 의상 150P·전용 코스튬 250P 표시와 기존 소유권을 확인합니다.
- 내 정보 & 설정: 활성 조건에 따라 쿠폰함·포인트 내역이 정상 표시되는지 확인합니다.
- 새 코칭·콜라보 화면은 기능 플래그 조건을 따릅니다. migration 완료가 자동 공개를 의미하지 않습니다.

`.env.example`의 `REWARD_COLLAB_DEMO_ENABLED=false`, `REWARD_COACHING_ENABLED=false`는 기본값입니다. 이번 DB 업데이트를 위해 임의로 true로 바꿀 필요가 없습니다. 교환 기능도 기존 활성 조건을 유지합니다. 플래그를 변경했다면 백엔드 재시작이 필요합니다.

## 5. 오류가 나면

| 증상 | 확인·조치 |
|---|---|
| `column ... does not exist`, `relation ... does not exist` | 앱이 연결한 DB에서 `alembic current`를 확인하고 마이그레이션을 적용합니다. 다른 DB에 적용하지 않았는지 확인합니다. |
| Docker 연결 실패 | Docker Desktop과 DB 컨테이너 상태를 확인합니다. |
| DB 인증·접속 실패 | 개인 `.env`와 현재 실행 방식의 DB 연결 대상을 확인합니다. 비밀번호를 채팅·GitHub에 올리지 않습니다. |
| `Can't locate revision`, `Multiple heads` | 코드 버전과 migration 파일을 확인합니다. 임의로 `stamp head`하거나 migration 파일을 삭제하지 않습니다. |
| `already exists`, 중간 단계 실패 | 추가 실행을 멈추고 현재 revision·오류 로그를 DB 담당자에게 전달합니다. DB 테이블을 임의 삭제하지 않습니다. |
| Docker 백엔드가 바로 종료됨 | `docker compose logs --tail 100 backend`에서 migration·시드 오류를 확인합니다. |

**되돌리기는 별도 판단이 필요합니다.** 이번 downgrade는 새 컬럼·코칭 테이블을 삭제하므로 추가된 데이터를 잃습니다. 상품 비활성화도 자동 복원하지 않습니다. 오류 해결 목적으로 downgrade·백업 복원을 임의 실행하지 말고, 백업 파일과 적용 revision을 확인한 뒤 DB 담당자와 진행합니다.

## 6. 팀원 완료 보고 양식

```text
실행 방식: Docker Backend / 로컬 Python Backend
백업: 완료 (파일은 개인 보관)
현재 revision: 20261022_02 (head)
DB health: ok
리워드몰·상세·꾸미기·활성화된 쿠폰함 확인: 완료 / 확인 필요
오류: 없음 / 비밀정보를 제외한 오류 내용
```
