# TEST-ONLY: 개인 브랜치 한정, 팀 반영 시 Backend Core A 담당 이관.
# 채팅 식사기록 A0: meal_items 섭취 비율·version 컬럼과 mutation_requests 테이블 추가(additive only).
# 기존 컬럼·제약·행 데이터는 변경하지 않는다. 기존 행은 server_default로 consumption_ratio=1, version=1이 된다.
"""Chat record A0: meal item consumption ratio, version and mutation requests."""
from alembic import op
import sqlalchemy as sa

revision = "20261015_01"
down_revision = "20261002_02"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('meal_items', sa.Column('consumption_ratio', sa.Float(), nullable=False, server_default='1'))
    op.add_column('meal_items', sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
    op.create_check_constraint('ck_meal_items_consumption_ratio', 'meal_items',
                               'consumption_ratio >= 0 AND consumption_ratio <= 1')
    op.create_check_constraint('ck_meal_items_version', 'meal_items', 'version >= 1')
    op.create_table('mutation_requests',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('operation', sa.String(length=40), nullable=False),
    sa.Column('request_id', sa.String(length=36), nullable=False),
    sa.Column('target_type', sa.String(length=20), nullable=False),
    sa.Column('target_id', sa.String(length=36), nullable=False),
    sa.Column('payload_hash', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('result_id', sa.String(length=36), nullable=True),
    sa.Column('result_version', sa.Integer(), nullable=True),
    sa.Column('before', sa.JSON(), nullable=True),
    sa.Column('after', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'operation', 'request_id', name='uq_mutation_requests_key')
    )
    op.create_index(op.f('ix_mutation_requests_user_id'), 'mutation_requests', ['user_id'], unique=False)


def downgrade():
    op.drop_index(op.f('ix_mutation_requests_user_id'), table_name='mutation_requests')
    op.drop_table('mutation_requests')
    op.drop_constraint('ck_meal_items_version', 'meal_items', type_='check')
    op.drop_constraint('ck_meal_items_consumption_ratio', 'meal_items', type_='check')
    op.drop_column('meal_items', 'version')
    op.drop_column('meal_items', 'consumption_ratio')
