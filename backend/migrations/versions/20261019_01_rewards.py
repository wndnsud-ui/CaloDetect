"""Reward Stage A (CaloPoint 원장·아이템·닉네임); user authorized scope and migration authorship 2026-10-19.

데이터 단계: 출시 시점의 기존 커뮤니티 포인트 잔액(point_transactions 합계 > 0)을 회원별 community_legacy lot 1건으로 옮긴다.
기존 테이블은 바꾸지 않는다. FK CASCADE 없음.
"""
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from alembic import op
import sqlalchemy as sa

revision = '20261019_01'
down_revision = '20261016_01'
branch_labels = None
depends_on = None

STAMP = sa.DateTime(timezone=True)


def upgrade():
    op.create_table('reward_accounts',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('balance_cache', sa.Integer(), nullable=False),
        sa.Column('xp_total_cache', sa.Integer(), nullable=False),
        sa.Column('level', sa.Integer(), nullable=False),
        sa.Column('goal_ref', sa.String(80)),
        sa.Column('created_at', STAMP, nullable=False), sa.Column('updated_at', STAMP, nullable=False))
    op.create_table('reward_grant_batches',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('meal_id', sa.String(36), sa.ForeignKey('meals.id')),
        sa.Column('skip_reason', sa.String(32)),
        sa.Column('created_at', STAMP, nullable=False))
    op.create_index('ix_reward_grant_batches_user_id', 'reward_grant_batches', ['user_id'])
    op.create_index('ix_reward_grant_batches_meal_id', 'reward_grant_batches', ['meal_id'])
    op.create_table('reward_point_lots',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('source', sa.String(24), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False), sa.Column('remaining', sa.Integer(), nullable=False),
        sa.Column('earned_at', STAMP, nullable=False), sa.Column('expires_at', STAMP, nullable=False),
        sa.Column('ref_type', sa.String(24)), sa.Column('ref_id', sa.String(64)),
        sa.Column('idem_key', sa.String(120), nullable=False),
        sa.Column('restricted', sa.Boolean(), nullable=False),
        sa.Column('batch_id', sa.String(36), sa.ForeignKey('reward_grant_batches.id')),
        sa.UniqueConstraint('user_id', 'idem_key', name='uq_reward_lots_idem'),
        sa.CheckConstraint('amount > 0', name='ck_reward_lots_amount'),
        sa.CheckConstraint('remaining >= 0 AND remaining <= amount', name='ck_reward_lots_remaining'))
    op.create_index('ix_reward_point_lots_user_id', 'reward_point_lots', ['user_id'])
    op.create_index('ix_reward_point_lots_batch_id', 'reward_point_lots', ['batch_id'])
    op.create_index('ix_reward_lots_user_expiry', 'reward_point_lots', ['user_id', 'expires_at'])
    op.create_table('reward_point_spends',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False), sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('ref_type', sa.String(24)), sa.Column('ref_id', sa.String(64)),
        sa.Column('created_at', STAMP, nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_reward_spends_amount'))
    op.create_index('ix_reward_point_spends_user_id', 'reward_point_spends', ['user_id'])
    op.create_table('reward_point_allocations',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('spend_id', sa.String(36), sa.ForeignKey('reward_point_spends.id'), nullable=False),
        sa.Column('lot_id', sa.String(36), sa.ForeignKey('reward_point_lots.id'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_reward_allocations_amount'))
    op.create_index('ix_reward_point_allocations_spend_id', 'reward_point_allocations', ['spend_id'])
    op.create_index('ix_reward_point_allocations_lot_id', 'reward_point_allocations', ['lot_id'])
    op.create_table('reward_debts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False), sa.Column('remaining', sa.Integer(), nullable=False),
        sa.Column('reason', sa.String(16), nullable=False),
        sa.Column('ref_type', sa.String(24)), sa.Column('ref_id', sa.String(64)),
        sa.Column('created_at', STAMP, nullable=False),
        sa.CheckConstraint('amount > 0', name='ck_reward_debts_amount'),
        sa.CheckConstraint('remaining >= 0 AND remaining <= amount', name='ck_reward_debts_remaining'))
    op.create_index('ix_reward_debts_user_id', 'reward_debts', ['user_id'])
    op.create_table('reward_xp_events',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False), sa.Column('source', sa.String(24), nullable=False),
        sa.Column('counts_for_ranking', sa.Boolean(), nullable=False),
        sa.Column('event_date', sa.Date(), nullable=False),
        sa.Column('ref_type', sa.String(24)), sa.Column('ref_id', sa.String(64)),
        sa.Column('idem_key', sa.String(120), nullable=False),
        sa.Column('batch_id', sa.String(36), sa.ForeignKey('reward_grant_batches.id')),
        sa.Column('created_at', STAMP, nullable=False),
        sa.UniqueConstraint('user_id', 'idem_key', name='uq_reward_xp_idem'))
    for column in ('user_id', 'event_date', 'batch_id'):
        op.create_index(f'ix_reward_xp_events_{column}', 'reward_xp_events', [column])
    op.create_table('reward_items',
        sa.Column('id', sa.String(40), primary_key=True),
        sa.Column('name', sa.String(60), nullable=False), sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('slot', sa.String(16), nullable=False), sa.Column('price', sa.Integer()),
        sa.Column('level_required', sa.Integer()), sa.Column('sellable', sa.Boolean(), nullable=False),
        sa.Column('stage', sa.String(1), nullable=False), sa.Column('asset_key', sa.String(40), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False), sa.Column('sort_order', sa.Integer(), nullable=False))
    op.create_table('reward_user_items',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('item_id', sa.String(40), sa.ForeignKey('reward_items.id'), primary_key=True),
        sa.Column('quantity', sa.Integer(), nullable=False), sa.Column('acquired_via', sa.String(16), nullable=False),
        sa.Column('created_at', STAMP, nullable=False),
        sa.CheckConstraint('quantity >= 0', name='ck_reward_user_items_quantity'))
    op.create_table('reward_equipment',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('slot', sa.String(16), primary_key=True),
        sa.Column('item_id', sa.String(40), sa.ForeignKey('reward_items.id'), nullable=False))
    op.create_table('reward_photo_hashes',
        sa.Column('sha256', sa.String(64), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('meal_id', sa.String(36), sa.ForeignKey('meals.id'), nullable=False),
        sa.Column('created_at', STAMP, nullable=False))
    op.create_index('ix_reward_photo_hashes_user_id', 'reward_photo_hashes', ['user_id'])
    op.create_table('reward_nicknames',
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
        sa.Column('nickname', sa.String(40), nullable=False),
        sa.Column('nickname_key', sa.String(40), nullable=False, unique=True),
        sa.Column('generated', sa.Boolean(), nullable=False), sa.Column('set_via', sa.String(16), nullable=False),
        sa.Column('changed_at', STAMP), sa.Column('prompt_dismissed_at', STAMP),
        sa.Column('created_at', STAMP, nullable=False), sa.Column('updated_at', STAMP, nullable=False))

    # 데이터 단계: 기존 커뮤니티 잔액 → community_legacy lot(잔액 0 이하는 만들지 않음). 교환 제외 출처다.
    bind = op.get_bind()
    lots = sa.table('reward_point_lots', *[sa.column(c) for c in (
        'id', 'user_id', 'source', 'amount', 'remaining', 'earned_at', 'expires_at', 'ref_type', 'ref_id',
        'idem_key', 'restricted', 'batch_id')])
    now = datetime.now(timezone.utc)
    rows = bind.execute(sa.text('SELECT user_id, SUM(amount) AS total FROM point_transactions '
                                'GROUP BY user_id HAVING SUM(amount) > 0')).all()
    if rows:
        op.bulk_insert(lots, [{'id': str(uuid4()), 'user_id': row.user_id, 'source': 'community_legacy',
            'amount': int(row.total), 'remaining': int(row.total), 'earned_at': now,
            'expires_at': now + timedelta(days=365), 'ref_type': 'migration', 'ref_id': revision,
            'idem_key': 'community_legacy', 'restricted': False, 'batch_id': None} for row in rows])


def downgrade():
    for name in ('reward_nicknames', 'reward_photo_hashes', 'reward_equipment', 'reward_user_items', 'reward_items',
                 'reward_xp_events', 'reward_debts', 'reward_point_allocations', 'reward_point_spends',
                 'reward_point_lots', 'reward_grant_batches', 'reward_accounts'):
        op.drop_table(name)
