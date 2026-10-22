"""Reward mall v1.3 M1: product catalog columns, exchange quantity/option (리워드몰 v1.3 지시서 §4-1·§4-2).

기존 컬럼은 바꾸지 않고 추가만 한다. 기존 교환 행은 quantity=1, option_label=null.
AI 서비스 탭 제거·코칭 이용권 전환 결정에 따라 ai_report·pro_coaching은 1회 비활성화한다(삭제하지 않음).
"""
from alembic import op
import sqlalchemy as sa

revision = '20261022_01'
down_revision = '20261020_01'
branch_labels = None
depends_on = None


def upgrade():
    with op.batch_alter_table('reward_products') as table:
        table.add_column(sa.Column('subcategory', sa.String(20)))
        table.add_column(sa.Column('list_price_won', sa.Integer()))
        table.add_column(sa.Column('options', sa.JSON(), nullable=False, server_default='[]'))
        table.add_column(sa.Column('max_qty', sa.Integer(), nullable=False, server_default='1'))
        table.add_column(sa.Column('listed', sa.Boolean(), nullable=False, server_default=sa.true()))
        table.add_column(sa.Column('collab_brand', sa.String(40)))
        # FK는 코치 테이블을 만드는 20261022_02에서 건다.
        table.add_column(sa.Column('coach_id', sa.String(40)))
        table.add_column(sa.Column('content', sa.JSON(), nullable=False, server_default='{}'))
        table.add_column(sa.Column('is_mock', sa.Boolean(), nullable=False, server_default=sa.true()))
        table.create_check_constraint('ck_reward_products_max_qty', 'max_qty >= 1 AND max_qty <= 9')
        table.create_check_constraint('ck_reward_products_list_price', 'list_price_won IS NULL OR list_price_won > 0')
    with op.batch_alter_table('reward_exchanges') as table:
        table.add_column(sa.Column('quantity', sa.Integer(), nullable=False, server_default='1'))
        table.add_column(sa.Column('option_label', sa.String(40)))
        table.create_check_constraint('ck_reward_exchanges_quantity', 'quantity >= 1')
    op.execute("UPDATE reward_products SET active = false WHERE id IN ('ai_report', 'pro_coaching')")


def downgrade():
    with op.batch_alter_table('reward_exchanges') as table:
        table.drop_constraint('ck_reward_exchanges_quantity', type_='check')
        table.drop_column('option_label')
        table.drop_column('quantity')
    with op.batch_alter_table('reward_products') as table:
        table.drop_constraint('ck_reward_products_list_price', type_='check')
        table.drop_constraint('ck_reward_products_max_qty', type_='check')
        for name in ('is_mock', 'content', 'coach_id', 'collab_brand', 'listed', 'max_qty', 'options', 'list_price_won', 'subcategory'):
            table.drop_column(name)
