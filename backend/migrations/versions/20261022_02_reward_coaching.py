"""Reward mall v1.3 M4: coaching pass tables (REWARD_COACHING_ENABLED 플래그 뒤, 지시서 §4-4).

FK CASCADE는 쓰지 않는다. 연락처(kakao_link·phone)는 시드에서 자리표시 값만 쓴다.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261022_02'
down_revision = '20261022_01'
branch_labels = None
depends_on = None

STAMP = sa.DateTime(timezone=True)


def upgrade():
    op.create_table('reward_coach_profiles',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('name', sa.String(40), nullable=False), sa.Column('headline', sa.String(80), nullable=False),
        sa.Column('specialties', sa.JSON(), nullable=False), sa.Column('quote', sa.String(200), nullable=False),
        sa.Column('philosophy', sa.String(200), nullable=False), sa.Column('career', sa.JSON(), nullable=False),
        sa.Column('introduction', sa.String(600), nullable=False), sa.Column('steps', sa.JSON(), nullable=False),
        sa.Column('rating_text', sa.String(10), nullable=False), sa.Column('coaching_count', sa.Integer(), nullable=False),
        sa.Column('profile_image_key', sa.String(120)), sa.Column('side_image_key', sa.String(120)),
        sa.Column('kakao_link', sa.String(300), nullable=False), sa.Column('phone', sa.String(20), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False), sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.Column('is_mock', sa.Boolean(), nullable=False))
    op.create_table('reward_coach_contents',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('coach_id', sa.String(40), sa.ForeignKey('reward_coach_profiles.id'), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False), sa.Column('label', sa.String(20), nullable=False),
        sa.Column('title', sa.String(120), nullable=False), sa.Column('body', sa.String(400), nullable=False),
        sa.Column('image_key', sa.String(120)), sa.Column('sort_order', sa.Integer(), nullable=False))
    op.create_index('ix_reward_coach_contents_coach_id', 'reward_coach_contents', ['coach_id'])
    op.create_table('reward_coach_passes',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('coach_id', sa.String(40), sa.ForeignKey('reward_coach_profiles.id'), nullable=False),
        sa.Column('product_id', sa.String(40), sa.ForeignKey('reward_products.id'), nullable=False),
        sa.Column('sessions', sa.Integer(), nullable=False), sa.Column('points', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(16), nullable=False),
        sa.Column('purchased_at', STAMP, nullable=False), sa.Column('closed_at', STAMP),
        sa.Column('spend_id', sa.String(36), sa.ForeignKey('reward_point_spends.id'), nullable=False),
        sa.Column('idem_key', sa.String(120), nullable=False),
        sa.UniqueConstraint('user_id', 'idem_key', name='uq_reward_coach_passes_idem'),
        sa.CheckConstraint("status IN ('in_use','completed','refunded')", name='ck_reward_coach_passes_status'),
        sa.CheckConstraint('points > 0', name='ck_reward_coach_passes_points'))
    op.create_index('ix_reward_coach_passes_user_coach_status', 'reward_coach_passes', ['user_id', 'coach_id', 'status'])
    with op.batch_alter_table('reward_products') as table:
        table.create_foreign_key('fk_reward_products_coach_id', 'reward_coach_profiles', ['coach_id'], ['id'])


def downgrade():
    with op.batch_alter_table('reward_products') as table:
        table.drop_constraint('fk_reward_products_coach_id', type_='foreignkey')
    op.drop_table('reward_coach_passes')
    op.drop_table('reward_coach_contents')
    op.drop_table('reward_coach_profiles')
