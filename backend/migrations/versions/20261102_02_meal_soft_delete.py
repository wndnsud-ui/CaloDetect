"""Meal deletion (2026-11-02 사용자 요청): meals.deleted_at 추가.

게시물·리워드 지급 묶음·사진 중복 기록이 meals를 참조하므로 행을 지우지 않고 삭제 시각만 남긴다.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261102_02'
down_revision = '20261102_01'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('meals', sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True))


def downgrade():
    op.drop_column('meals', 'deleted_at')
