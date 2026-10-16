"""Community v5; user authorized model/migration authorship 2026-10-16."""
from alembic import op
import sqlalchemy as sa

revision = '20261016_01'
down_revision = '20261015_02'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('community_posts',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('meal_id', sa.String(36), sa.ForeignKey('meals.id'), nullable=False, unique=True),
        sa.Column('comment', sa.String(300), nullable=False),
        sa.Column('show_photo', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)))
    op.create_index('ix_community_posts_user_id', 'community_posts', ['user_id'])
    op.create_index('ix_community_posts_created_at', 'community_posts', ['created_at'])
    op.create_index('ix_community_feed_cursor', 'community_posts', [sa.text('created_at DESC'), sa.text('id DESC')])
    op.create_table('community_post_images',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('post_id', sa.String(36), sa.ForeignKey('community_posts.id'), nullable=False),
        sa.Column('source_image_id', sa.String(36), nullable=False),
        sa.Column('storage_key', sa.String(255), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('post_id', 'position'))
    op.create_index('ix_community_post_images_post_id', 'community_post_images', ['post_id'])
    op.create_table('community_reactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('post_id', sa.String(36), sa.ForeignKey('community_posts.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('kind', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('post_id', 'user_id', 'kind'), sa.CheckConstraint("kind IN ('like', 'recommend')"))
    for column in ('post_id', 'user_id'):
        op.create_index(f'ix_community_reactions_{column}', 'community_reactions', [column])
    op.create_table('point_transactions',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False), sa.Column('reason', sa.String(32), nullable=False),
        sa.Column('post_id', sa.String(36), sa.ForeignKey('community_posts.id')),
        sa.Column('reaction_id', sa.String(36)),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False))
    for column in ('user_id', 'post_id', 'reaction_id', 'created_at'):
        op.create_index(f'ix_point_transactions_{column}', 'point_transactions', [column])
    op.create_index('uq_point_tx_reaction_reason', 'point_transactions', ['reaction_id', 'reason'], unique=True,
        postgresql_where=sa.text('reaction_id IS NOT NULL'), sqlite_where=sa.text('reaction_id IS NOT NULL'))
    op.create_index('uq_point_tx_post_deleted', 'point_transactions', ['post_id'], unique=True,
        postgresql_where=sa.text("reason = 'post_deleted_revoked'"), sqlite_where=sa.text("reason = 'post_deleted_revoked'"))


def downgrade():
    for name in ('point_transactions', 'community_reactions', 'community_post_images', 'community_posts'):
        op.drop_table(name)
