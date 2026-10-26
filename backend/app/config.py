# 프로젝트 루트의 비공개 .env와 환경변수를 Pydantic 설정으로 읽는다.
# 서비스 동의·이미지 저장·추천 등 정책 설정은 기능 사용 가능 여부를 제어하며 미설정 값을 임의 정책으로 채우지 않는다.
from datetime import datetime
from pathlib import Path
from typing import Literal
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[2]


# Settings: 환경변수/.env 설정 모델. 타입·허용값을 검증하며 settings 인스턴스를 모듈에서 공유한다.
class Settings(BaseSettings):
    community_like_received_points: int = Field(default=1, ge=0, le=100)
    community_recommend_received_points: int = Field(default=3, ge=0, le=100)
    community_reaction_given_points: int = Field(default=1, ge=0, le=100)
    community_ranking_size: int = Field(default=10, ge=1, le=100)
    model_config = SettingsConfigDict(env_file=ROOT / '.env', extra='ignore')
    # 서버 전용 PostgreSQL URL. 비공개 .env에서 읽으며 클라이언트 응답에 노출하지 않는다.
    database_url: str | None = None
    # Supabase pooler 방식. session(5432)은 연결 풀 재사용, transaction(6543)은 NullPool·prepared statement 비활성.
    db_pool_mode: Literal['session', 'transaction'] = 'session'
    # 원격 DB 연결 대기 초. 로컬 3초는 원격 pooler에 짧다.
    db_connect_timeout: int = Field(default=10, ge=1, le=120)
    # 시작 시 migration·seed 실행 여부. 공유 DB를 쓰는 팀원은 false로 두고 담당자 1명만 migration을 실행한다.
    run_migrations_on_start: bool = True
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
    # 사진 저장 위치: local(IMAGE_STORAGE_DIR 폴더) 또는 supabase(공유 DB용 Storage 비공개 버킷).
    image_storage_backend: Literal['local', 'supabase'] = 'local'
    supabase_url: str | None = None
    # Storage 서버 전용 비밀키(sb_secret 또는 service_role). 프런트엔드·응답에 노출하지 않는다.
    supabase_service_role_key: str | None = None
    supabase_storage_bucket: str = 'calodetect-images'
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
    # Google 앱의 공개 Client ID. ID 토큰 audience 검증 기준이다.
    google_client_id: str | None = None
    # Authorization Code 교환용 서버 비밀. 기본 GIS 인증에는 필요하지 않는다.
    google_client_secret: str | None = None
    # Google 등록 정보와 일치해야 하는 서버 callback URI.
    google_redirect_uri: str = 'http://localhost:8000/api/auth/google/callback'
    apple_client_id: str | None = None
    apple_redirect_uri: str | None = None
    kakao_client_id: str | None = None
    kakao_client_secret: str | None = None
    kakao_redirect_uri: str = 'http://localhost:8000/api/auth/kakao/callback'
    # state 서명과 가입 임시 정보 보호에 쓰는 서버 비밀키.
    oauth_state_secret: str | None = Field(default=None, min_length=32)
    # 채팅 식사기록·섭취량 수정 기능 플래그. false면 새 라우트·meal_json 추가 키·프론트 진입점이 없다.
    chat_record_enabled: bool = False
    # ---- CaloPoint·Growth·Reward(리워드 지시서 v3 §5-6). 모든 수치는 개발 기본값이며 운영값은 TBD ----
    reward_enabled: bool = True
    reward_point_valid_days: int = Field(default=365, ge=1)
    reward_meal_photo_points: int = Field(default=2, ge=0)
    reward_meal_text_points: int = Field(default=1, ge=0)
    reward_meal_xp: int = Field(default=10, ge=0)
    reward_snack_points: int = Field(default=1, ge=0)
    reward_snack_xp: int = Field(default=5, ge=0)
    reward_three_meals_points: int = Field(default=3, ge=0)
    reward_three_meals_xp: int = Field(default=10, ge=0)
    reward_three_meal_min_gap_minutes: int = Field(default=120, ge=0)
    reward_onboarding_signup: int = Field(default=10, ge=0)
    reward_onboarding_goal: int = Field(default=10, ge=0)
    reward_onboarding_first_meal: int = Field(default=10, ge=0)
    reward_daily_mission_points: int = Field(default=2, ge=0)
    reward_daily_mission_xp: int = Field(default=10, ge=0)
    reward_weekly_mission_points: int = Field(default=15, ge=0)
    reward_monthly_goal_points: int = Field(default=30, ge=0)
    reward_streak3_points: int = Field(default=5, ge=0)
    reward_streak3_xp: int = Field(default=20, ge=0)
    reward_streak7_points: int = Field(default=10, ge=0)
    reward_streak7_xp: int = Field(default=50, ge=0)
    reward_balance_xp: int = Field(default=15, ge=0)
    reward_balance_cal_tolerance: float = Field(default=0.15, ge=0, le=1)
    reward_share_points: int = Field(default=1, ge=0)
    reward_share_xp: int = Field(default=10, ge=0)
    reward_reaction_received_like_xp: int = Field(default=5, ge=0)
    reward_reaction_received_recommend_xp: int = Field(default=10, ge=0)
    reward_reaction_received_daily_cap: int = Field(default=50, ge=0)
    reward_reaction_given_xp: int = Field(default=2, ge=0)
    reward_reaction_given_daily_cap: int = Field(default=20, ge=0)
    reward_level_thresholds: str = '0,300,1000,2500,5000'
    reward_levelup_points: str = '0,0,50,100,200'
    reward_protector_monthly_limit: int = Field(default=2, ge=0)
    # 배포 시각(필수). 없으면 가입 온보딩 포인트를 지급하지 않고 모든 회원을 출시 이전 회원으로 본다.
    reward_onboarding_start_at: datetime | None = None
    reward_weekly_mission_days: int = Field(default=5, ge=1, le=7)
    reward_monthly_goal_days: int = Field(default=20, ge=1, le=31)
    reward_eta_window_days: int = Field(default=7, ge=1)
    reward_ranking_size: int = Field(default=10, ge=1, le=100)
    reward_nickname_min_len: int = Field(default=2, ge=1)
    reward_nickname_max_len: int = Field(default=12, ge=2, le=40)
    reward_nickname_change_days: int = Field(default=30, ge=0)
    reward_nickname_check_per_min: int = Field(default=30, ge=1)
    reward_nickname_suggest_per_min: int = Field(default=10, ge=1)
    # Stage B 전환 스위치: 커뮤니티 반응 보상을 포인트 대신 XP로, 식단 공유 +1P·+10XP.
    reward_community_xp_mode: bool = False
    reward_exchange_excluded_sources: str = 'onboarding,community,community_legacy'
    # Stage C 실물 교환·쿠폰함(지시서 v3 §2-5). 기본 꺼짐. 월 전체 상한이 없거나 0 이하이면 켜도 꺼진 것으로 본다.
    reward_exchange_enabled: bool = False
    reward_exchange_min_account_days: int = Field(default=14, ge=0)
    reward_exchange_monthly_limit: int = Field(default=1, ge=1)
    reward_exchange_first_hold: bool = True
    reward_exchange_global_monthly_cap: int | None = None
    # 리워드몰 v1.3: 콜라보 기획전(실존 브랜드, 내부 시연용)과 전문 코칭 이용권은 기본 꺼짐.
    reward_collab_demo_enabled: bool = False
    reward_coaching_enabled: bool = False

    # 교환 기능이 실제로 켜졌는지: 플래그 + 월 전체 상한 + 쿠폰 번호 암호화 키(OAUTH_STATE_SECRET).
    @property
    def reward_exchange_active(self):
        return bool(self.reward_exchange_enabled and (self.reward_exchange_global_monthly_cap or 0) > 0
                    and self.oauth_state_secret)

    # 쉼표 목록 설정을 정수 목록·집합으로 읽는다.
    @property
    def reward_levels(self):
        return [int(v) for v in self.reward_level_thresholds.split(',')]

    @property
    def reward_levelup_point_list(self):
        return [int(v) for v in self.reward_levelup_points.split(',')]

    @property
    def reward_excluded_sources(self):
        return {v.strip() for v in self.reward_exchange_excluded_sources.split(',') if v.strip()}


settings = Settings()
