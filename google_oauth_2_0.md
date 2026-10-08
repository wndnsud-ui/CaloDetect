# [업무 지시서] Google OAuth 2.0 로컬 회원가입 및 로그인 연동

> **현재 저장소 구현 안내:** 아래의 독립형 예제는 최초 요구사항을 설명하는 참고 자료이며 실행 코드가 아닙니다. 그대로 복사하면 state·nonce·PKCE 검증 및 안전한 세션 처리가 빠지고 이메일을 URL이나 localStorage에 저장하게 됩니다. 실제 구현은 `backend/app/social_auth.py`와 `frontend/src/SocialLogin.jsx`를 사용하며 실행·설정 절차는 README의 **Google 로그인 설정**을 따릅니다. Client Secret이 없는 새 PC에서는 Google Identity Services ID 토큰 흐름을 사용하고, Secret이 설정된 환경에서는 Authorization Code + PKCE 흐름을 사용합니다.

---

## 1. 개요 및 목적
* **과업명**: 로컬 개발 환경 Google OAuth 2.0 인증 연동
* **목적**: Google 계정을 통한 원클릭 간편 로그인 및 신규 회원 자동 등록 처리
* **작업 스택**:
  * Frontend: React / Vite (`http://localhost:5174`)
  * Backend: FastAPI (`http://localhost:8000`)
  * 프로토콜: Google Identity Services ID 토큰 또는 OAuth 2.0 Authorization Code + PKCE

---

## 2. 사전 완료 사항 (Google Cloud Console)
1. **OAuth 동의 화면 설정**
   * 사용자 유형: **외부(External)**
   * 게시 상태: **테스트(Testing)** 모드
   * 테스트 사용자(Test Users): 테스트용 구글 계정 등록 완료
2. **OAuth 2.0 클라이언트 자격 증명 발급**
   * 승인된 JavaScript 원본: `http://localhost:5174`
   * Authorization Code 흐름을 쓰는 경우에만 승인된 리디렉션 URI: `http://localhost:8000/api/auth/google/callback`
   * 환경 변수: 공개 `GOOGLE_CLIENT_ID`; `GOOGLE_CLIENT_SECRET`은 선택 사항

---

## 3. 세부 작업 지시 사항

### Task 1. 백엔드 환경 설정 및 API 엔드포인트 구현 (FastAPI)

1. **환경 변수 파일 구성 (`.env`)**
   ```env
   GOOGLE_CLIENT_ID=YOUR_GOOGLE_CLIENT_ID
   # Optional: omit on a new PC to use Google Identity Services
   GOOGLE_CLIENT_SECRET=YOUR_GOOGLE_CLIENT_SECRET
   GOOGLE_REDIRECT_URI=http://localhost:8000/api/auth/google/callback
   FRONTEND_URL=http://localhost:5174
   ```

2. **필수 라이브러리 설치**
   ```bash
   pip install httpx python-dotenv fastapi uvicorn
   ```

3. **인증 라우터**
   * 저장소의 실제 구현 경로는 `backend/app/social_auth.py`입니다. 아래 코드는 요구사항 전달 당시의 개념 예시이며 현재 앱의 경로·콜백 계약과 일치하지 않습니다.
   * **`GET /api/auth/google/login`**:
     * 사용자를 구글 로그인/동의 창으로 리디렉션.
     * 필수 요청 Scope: `openid`, `email`, `profile`
   * **`GET /api/auth/google/callback`**:
     * 구글이 전달한 인가 코드(`code`)를 수신.
     * 구글 토큰 서버(`https://oauth2.googleapis.com/token`)에 `code`와 `client_secret`을 전송하여 `access_token` 교환.
     * 구글 유저 정보 서버(`https://www.googleapis.com/oauth2/v2/userinfo`)를 호출하여 이메일, 이름, 프로필 수신.
     * DB 내 해당 유저 조회:
       * 신규 유저: 회원가입 레코드 생성 (INSERT)
       * 기존 유저: 로그인 처리 (SELECT)
     * 자체 서비스 인증 토큰(또는 세션) 발행 후 프론트엔드 URL(`http://localhost:5174/login-success`)로 리디렉션.

```python
# auth.py 구현 예시
import os
import urllib.parse
import httpx
from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["auth"])

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://localhost:8000/api/auth/google/callback")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5174")

@router.get("/google/login")
def login_google():
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    google_auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"
    return RedirectResponse(url=google_auth_url)

@router.get("/google/callback")
async def google_callback(code: str = None, error: str = None):
    if error or not code:
        raise HTTPException(status_code=400, detail="Google authentication failed")

    token_url = "https://oauth2.googleapis.com/token"
    token_data = {
        "code": code,
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "grant_type": "authorization_code",
    }

    async with httpx.AsyncClient() as client:
        token_resp = await client.post(token_url, data=token_data)
        if token_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to obtain token from Google")
        tokens = token_resp.json()
        access_token = tokens.get("access_token")

        userinfo_url = "https://www.googleapis.com/oauth2/v2/userinfo"
        userinfo_resp = await client.get(
            userinfo_url,
            headers={"Authorization": f"Bearer {access_token}"}
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(status_code=400, detail="Failed to obtain user profile")

        user_info = userinfo_resp.json()

    user_email = user_info.get("email")
    user_name = user_info.get("name")

    # TODO: DB 연동 로직
    # 1. user_email 기준으로 DB 사용자 검색
    # 2. 미존재 시 자동 회원가입 INSERT
    # 3. 자체 JWT Access Token 생성

    # 프론트엔드로 리다이렉트
    redirect_target = f"{FRONTEND_URL}/login-success?email={user_email}&name={urllib.parse.quote(user_name or '')}"
    return RedirectResponse(url=redirect_target)
```

---

### Task 2. 프론트엔드 버튼 및 수신 라우트 구현 (React)

1. **Google 로그인 버튼 컴포넌트 (`GoogleLoginButton.jsx`)**
   * 클릭 시 백엔드의 `/api/auth/google/login` 엔드포인트로 이동.

```jsx
// GoogleLoginButton.jsx
import React from 'react';

export default function GoogleLoginButton() {
  const handleGoogleLogin = () => {
    window.location.href = "http://localhost:8000/api/auth/google/login";
  };

  return (
    <button
      onClick={handleGoogleLogin}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        gap: "10px",
        padding: "10px 16px",
        border: "1px solid #dadce0",
        borderRadius: "4px",
        backgroundColor: "#ffffff",
        color: "#3c4043",
        fontSize: "14px",
        fontWeight: "500",
        cursor: "pointer"
      }}
    >
      <img
        src="https://developers.google.com/identity/images/g-logo.png"
        alt="Google logo"
        width="18"
        height="18"
      />
      Google 계정으로 계속하기
    </button>
  );
}
```

2. **로그인 완료 콜백 처리 페이지 (`LoginSuccess.jsx`)**
   * `/login-success` 경로에서 URL 파라미터(`email`, `token` 등)를 파싱하여 전역 상태(또는 localStorage)에 저장 후 메인 화면으로 전환.

```jsx
// LoginSuccess.jsx
import { useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

export default function LoginSuccess() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  useEffect(() => {
    const email = searchParams.get('email');
    const name = searchParams.get('name');

    if (email) {
      // 로컬 스토리지 또는 Context/Redux 상태에 저장
      localStorage.setItem('user', JSON.stringify({ email, name }));
      navigate('/dashboard', { replace: true });
    } else {
      navigate('/login?error=auth_failed', { replace: true });
    }
  }, [searchParams, navigate]);

  return <div>로그인 처리 중입니다... 잠시만 기다려주세요.</div>;
}
```

---

## 4. 검증 체크리스트

| 검증 항목 | 검증 방법 | 통과 기준 |
| :--- | :--- | :--- |
| **Google 로그인창 이동** | 프론트엔드 버튼 클릭 | `accounts.google.com` 로그인 화면 정상 출력 |
| **코드 수신 및 교환** | 계정 선택 및 권한 동의 | 백엔드 `/callback`에서 `access_token` 정상 수신 (HTTP 200) |
| **사용자 정보 파싱** | UserInfo 응답 확인 | `email`, `name`, `sub` 필드 유효값 확인 |
| **DB 회원 처리** | DB 레코드 확인 | 신규 유저는 신규 INSERT, 기존 유저는 기존 ID 매핑 |
| **프론트엔드 복귀** | 브라우저 리다이렉트 확인 | `localhost:5174/login-success`로 안전하게 이동 후 로그인 완료 |