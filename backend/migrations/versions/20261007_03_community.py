"""Backend Core A: authenticated community posts, reactions and comments."""
from alembic import op
import sqlalchemy as sa
revision='20261007_03'
down_revision='20261002_02'
branch_labels=None
depends_on=None
def upgrade():
    op.create_table('community_posts',sa.Column('id',sa.String(36),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('title',sa.String(120),nullable=False),sa.Column('text',sa.String(4000),nullable=False),sa.Column('category',sa.String(20),nullable=False),sa.Column('visibility',sa.String(20),nullable=False),sa.Column('image_name',sa.String(80)),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False),sa.CheckConstraint("visibility IN ('private', 'public')"))
    op.create_index('ix_community_posts_user_id','community_posts',['user_id'])
    op.create_index('ix_community_posts_created_at','community_posts',['created_at'])
    op.create_table('community_reactions',sa.Column('post_id',sa.String(36),sa.ForeignKey('community_posts.id',ondelete='CASCADE'),primary_key=True),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),primary_key=True),sa.Column('kind',sa.String(20),primary_key=True),sa.CheckConstraint("kind IN ('like', 'recommend')"))
    op.create_table('community_comments',sa.Column('id',sa.String(36),primary_key=True),sa.Column('post_id',sa.String(36),sa.ForeignKey('community_posts.id',ondelete='CASCADE'),nullable=False),sa.Column('user_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('text',sa.String(1000),nullable=False),sa.Column('created_at',sa.DateTime(timezone=True),nullable=False))
    op.create_index('ix_community_comments_post_id','community_comments',['post_id'])
def downgrade():
    op.drop_table('community_comments')
    op.drop_table('community_reactions')
    op.drop_table('community_posts')
