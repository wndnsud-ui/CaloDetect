"""Reward Stage B (레벨업 이벤트·연속 기록 보호); user authorized 2026-10-19."""
from alembic import op
import sqlalchemy as sa

revision = '20261019_02'
down_revision = '20261019_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('reward_level_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('seen_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'level', name='uq_reward_level_events'))
    op.create_index('ix_reward_level_events_user_id', 'reward_level_events', ['user_id'])
    op.create_table('reward_streak_protections',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('protected_date', sa.Date(), primary_key=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))


def downgrade():
    op.drop_table('reward_streak_protections')
    op.drop_table('reward_level_events')
