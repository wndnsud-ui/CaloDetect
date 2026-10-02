"""Backend Core A: members, revocable sessions and profiles."""
from alembic import op
import sqlalchemy as sa

revision = '20261002_01'
down_revision = None
branch_labels = None
depends_on = None


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


def downgrade():
    op.drop_table('user_profiles')
    op.drop_index('ix_auth_sessions_user_id', table_name='auth_sessions')
    op.drop_table('auth_sessions')
    op.drop_table('users')
