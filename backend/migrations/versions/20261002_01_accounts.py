# 기존 회원·인증 테이블의 Alembic revision. upgrade는 적용, downgrade는 이 revision의 변경을 되돌린다.
# 아래 revision 식별자와 테이블 정의는 기존 migration 이력을 유지한다.
"""Backend Core A: members, revocable sessions and profiles."""
from alembic import op
import sqlalchemy as sa

revision = '20261002_01'
down_revision = None
branch_labels = None
depends_on = None


# 이 revision의 테이블·인덱스·제약을 적용한다. 기존 적용 여부는 Alembic revision 이력으로 관리한다.
def upgrade():
    op.create_table('users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(254), nullable=False, unique=True),
        sa.Column('name', sa.String(80), nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('service_consent_text', sa.String(4000), nullable=False),
        sa.Column('service_consent_at', sa.DateTime(timezone=True), nullable=False))
    op.create_table('auth_sessions',
        sa.Column('token_hash', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('csrf_token', sa.String(64), nullable=False))
    op.create_index('ix_auth_sessions_user_id', 'auth_sessions', ['user_id'])
    op.create_table('user_profiles',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('data', sa.JSON(), nullable=False))


# 이 revision의 스키마 변경을 역순으로 되돌린다. 실제 실행 시 해당 테이블의 데이터가 제거될 수 있다.
def downgrade():
    op.drop_table('user_profiles')
    op.drop_index('ix_auth_sessions_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_table('users')
