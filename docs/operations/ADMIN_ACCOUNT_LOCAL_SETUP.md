# 관리자 메뉴가 안 보일 때 (각자 PC에서)

DB는 PC마다 따로라서, `git pull`을 해도 계정은 오지 않습니다. 관리자 계정은 **각자 PC에서 한 번 만들어야** 합니다.
모든 명령은 **CaloDetect 프로젝트 폴더**의 PowerShell에서 실행합니다. 자세한 설치·실행은 [팀원 로컬 테스트 가이드](TEAM_LOCAL_TEST_GUIDE.md)를 참고하세요.

## 1단계: `.env` 확인

아래 세 줄이 있어야 합니다. 바꿨다면 백엔드를 다시 켜 주세요.

```dotenv
APP_ENV=development
LOCAL_TEST_SIGNUP=true
FRONTEND_ORIGIN=http://localhost:5174
```

## 2단계: 관리자 계정 만들기

백엔드를 어떻게 실행하는지에 따라 **둘 중 하나만** 실행합니다.

**A. 백엔드도 Docker로 실행하는 경우**

```powershell
docker compose exec backend python -m backend.scripts.seed_local_admin
```

**B. Docker는 DB만, 백엔드는 PC에서 실행하는 경우**

```powershell
.\.venv-backend\Scripts\python.exe -m backend.scripts.seed_local_admin
```

## 3단계: 결과 메시지 보고 다음 할 일

| 나온 메시지 | 다음 할 일 |
|---|---|
| `Local admin created` | 끝. 4단계로 갑니다. |
| `already exists; unchanged` | 이미 관리자입니다. 4단계로 갑니다. |
| `exists as a normal user; not promoted` | 같은 이메일로 일반 가입이 먼저 되어 있습니다. 아래 **3-1**을 진행합니다. |
| `Local development test settings required` | 1단계 `.env`를 다시 확인합니다. |

### 3-1. 일반 회원을 관리자로 바꾸기 (본인 PC의 개발 DB에서만)

```powershell
docker compose exec db psql -U calodetect_develop -d calodetect_develop -c "UPDATE users SET role='admin' WHERE email='admin@calodetect.local';"
```

- `UPDATE 1`이 나오면 성공입니다.
- `.env`에서 `POSTGRES_USER`나 `POSTGRES_DB`를 바꿨다면 `calodetect_develop` 두 군데를 본인 값으로 바꿔 실행합니다.
- 비밀번호는 그대로 유지됩니다. 일반 가입할 때 정한 비밀번호로 로그인합니다.
- DB를 직접 고치는 명령입니다. **운영 DB나 다른 사람 DB에서는 실행하지 않습니다.**

## 4단계: 로그인 확인

1. http://localhost:5174 에 접속하고, 이미 로그인되어 있으면 **로그아웃**합니다.
2. **이메일 로그인**을 선택합니다. Google·카카오 로그인이 아닙니다.
3. `admin@calodetect.local` / `CaloAdmin!2026`로 로그인합니다.
4. **관리자** 버튼이 왼쪽 사이드바 **아래쪽 '내 정보 & 설정' 밑**에 생깁니다.
   - 메뉴 정리(2026-10-22)로 위치가 바뀌었습니다. 예전처럼 메뉴 목록 안에 있지 않습니다.
   - 모바일에서는 화면 오른쪽 위 작은 버튼입니다.

> `test@calodetect.local`은 일반 테스트 회원이라 관리자 메뉴가 나오지 않습니다. 대신 **테스트** 메뉴가 나옵니다.
