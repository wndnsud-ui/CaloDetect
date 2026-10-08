# 프로젝트 루트의 비공개 .env와 환경변수를 Pydantic 설정으로 읽는다.
# 서비스 동의·이미지 저장·추천 등 정책 설정은 기능 사용 가능 여부를 제어하며 미설정 값을 임의 정책으로 채우지 않는다.
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


# Settings: 환경변수/.env 설정 모델. 타입·허용값을 검증하며 settings 인스턴스를 모듈에서 공유한다.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    # 서버 전용 PostgreSQL URL. 비공개 .env에서 읽으며 클라이언트 응답에 노출하지 않는다.
    database_url: str | None = None
    # development/production 구분. 테스트 플래그만으로 운영 환경의 제한을 해제하지 않는다.
    app_env: Literal['development', 'production'] = 'production'
    # 명시적인 로컬 가입 테스트 허용 플래그. loopback 환경/요청 검사도 통과해야 한다.
    local_test_signup: bool = False
    # 명시적인 로컬 사진 분석 테스트 플래그. 운영 이미지 보관 정책 승인과 다르다.
    local_test_image_analysis: bool = False
    # 허용할 브라우저 원본과 메일/소셜 인증 반환 주소의 기준.
    frontend_origin: str = 'http://localhost:5174'
    # 가입·프로필의 최소 만 나이. 현재 확정 기준은 18세다.
    age_min: int | None = Field(default=18, ge=18, le=120)
    # 서버 사진 저장 폴더. 상대 경로면 프로젝트 루트 기준으로 해석한다.
    image_storage_dir: str | None = None
    # 개발 추천 사용 여부. 최근 식사 window 설정도 함께 필요하다.
    recommendation_enabled: bool = False
    # 최근 중복 판정에 조회할 식단 수. 운영 정책을 새로 확정하는 값은 아니다.
    recent_meal_window: int | None = None
    # 쿠키를 HTTPS로만 전송할지 선택한다. HTTPS 운영 환경에서 활성화한다.
    cookie_secure: bool = False
    # 로그인 세션의 시간 단위 유효기간.
    session_hours: int = 24
    # 재설정 링크의 HMAC 서버 비밀키. Client에 전달하지 않는다.
    password_reset_secret: str | None = Field(default=None, min_length=32)
    smtp_host: str | None = None
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_username: str | None = None
    # 서버 SMTP 자격정보. Gmail은 앱 비밀번호를 사용하며 Git에 저장하지 않는다.
    smtp_password: str | None = None
    smtp_from: str | None = None
    # 메일 전송 TLS 방식: STARTTLS 또는 SSL.
    smtp_security: Literal['starttls', 'ssl'] = 'starttls'
    # 가입 때 확인한 서비스 필수 동의 문구를 기록한다.
    service_consent_text: str | None = None
    model_improvement_consent_text: str | None = None
    # Google 앱의 공개 Client ID. ID 토큰 audience 검증 기준이다.
    google_client_id: str | None = None
    # Authorization Code 교환용 서버 비밀. 기본 GIS 인증에는 필요하지 않는다.
    google_client_secret: str | None = None
    # Google 등록 정보와 일치해야 하는 서버 callback URI.
    google_redirect_uri: str = 'http://localhost:8000/api/auth/google/callback'
    apple_client_id: str | None = None
    apple_redirect_uri: str | None = None
    # state 서명과 가입 임시 정보 보호에 쓰는 서버 비밀키.
    oauth_state_secret: str | None = Field(default=None, min_length=32)


settings = Settings()
