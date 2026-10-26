"""커뮤니티 댓글 테이블(사용자 결정 2026-10-26: 보상 없음, 작성자·게시물 주인·관리자 삭제).

새 테이블만 추가한다. PostgreSQL에서는 기존 테이블과 같게 RLS를 켠다(정책 없음, Data API 노출 차단).
"""
from alembic import op
import sqlalchemy as sa

revision = '20261027_01'
down_revision = '20261026_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('community_comments',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('post_id', sa.String(36), sa.ForeignKey('community_posts.id'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('body', sa.String(300), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True)))
    op.create_index('ix_community_comments_post_created', 'community_comments', ['post_id', 'created_at'])
    op.create_index('ix_community_comments_user_id', 'community_comments', ['user_id'])
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE public.community_comments ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_index('ix_community_comments_user_id', 'community_comments')
    op.drop_index('ix_community_comments_post_created', 'community_comments')
    op.drop_table('community_comments')
