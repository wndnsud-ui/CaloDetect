"""Reward Stage C (건강상품 교환·쿠폰함, REWARD_EXCHANGE_ENABLED 플래그 뒤); user requested 2026-10-20."""
from alembic import op
import sqlalchemy as sa

revision = '20261019_03'
down_revision = '20261019_02'
branch_labels = None
depends_on = None

STAMP = sa.DateTime(timezone=True)


def upgrade():
    op.create_table('reward_products',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('name', sa.String(60), nullable=False), sa.Column('category', sa.String(16), nullable=False),
        sa.Column('price', sa.Integer(), nullable=False), sa.Column('available', sa.Boolean(), nullable=False),
        sa.Column('partner_label', sa.String(60), nullable=False), sa.Column('description', sa.String(200), nullable=False),
        sa.Column('image_key', sa.String(120)), sa.Column('active', sa.Boolean(), nullable=False),
        sa.Column('sort_order', sa.Integer(), nullable=False),
        sa.CheckConstraint('price > 0', name='ck_reward_products_price'))
    op.create_table('reward_exchanges',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('product_id', sa.String(40), sa.ForeignKey('reward_products.id'), nullable=False),
        sa.Column('points', sa.Integer(), nullable=False), sa.Column('status', sa.String(16), nullable=False),
        sa.Column('first_exchange', sa.Boolean(), nullable=False),
        sa.Column('requested_at', STAMP, nullable=False), sa.Column('issued_at', STAMP), sa.Column('closed_at', STAMP),
        sa.Column('coupon_code_enc', sa.String(400)), sa.Column('coupon_expires_at', STAMP), sa.Column('used_marked_at', STAMP),
        sa.Column('month_key', sa.String(7), nullable=False),
        sa.Column('spend_id', sa.String(36), sa.ForeignKey('reward_point_spends.id'), nullable=False),
        sa.CheckConstraint("status IN ('requested','held','issued','used','canceled','failed')", name='ck_reward_exchanges_status'),
        sa.CheckConstraint('points > 0', name='ck_reward_exchanges_points'))
    op.create_index('ix_reward_exchanges_user_id', 'reward_exchanges', ['user_id'])
    op.create_index('ix_reward_exchanges_month_key', 'reward_exchanges', ['month_key'])
    op.create_table('reward_exchange_month_counters',
        sa.Column('month_key', sa.String(7), primary_key=True),
        sa.Column('active_count', sa.Integer(), nullable=False),
        sa.CheckConstraint('active_count >= 0', name='ck_reward_exchange_counter'))


def downgrade():
    op.drop_table('reward_exchange_month_counters')
    op.drop_table('reward_exchanges')
    op.drop_table('reward_products')
