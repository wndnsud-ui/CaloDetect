"""모델 개선(재학습) 폐기: retraining_samples 테이블과 users의 모델 개선 동의 컬럼 삭제.

2026-10-20 사용자 결정: "모델개선은 폐기, DB까지 완전 삭제". 기존 학습 후보·동의 기록은 복구할 수 없다.
downgrade는 빈 테이블·기본값 컬럼만 다시 만든다(데이터는 돌아오지 않음).
"""
from alembic import op
import sqlalchemy as sa

revision = '20261020_01'
down_revision = '20261019_03'
branch_labels = None
depends_on = None


def upgrade():
    op.drop_index('ix_retraining_samples_detection_log_id', table_name='retraining_samples')
    op.drop_table('retraining_samples')
    op.drop_column('users', 'model_improvement_consent_at')
    op.drop_column('users', 'model_improvement_consent')


def downgrade():
    op.add_column('users', sa.Column('model_improvement_consent', sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column('users', sa.Column('model_improvement_consent_at', sa.DateTime(timezone=True), nullable=True))
    op.create_table('retraining_samples',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('detection_log_id', sa.String(36), sa.ForeignKey('detection_logs.id'), nullable=False),
        sa.Column('image_path', sa.String(255), nullable=False),
        sa.Column('predicted_label', sa.String(120), nullable=False),
        sa.Column('corrected_label', sa.String(120), nullable=False),
        sa.Column('qa_status', sa.String(16), nullable=False),
        sa.Column('excluded', sa.Boolean(), nullable=False),
        sa.Column('approved_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("qa_status IN ('PENDING','APPROVED','REJECTED')"))
    op.create_index('ix_retraining_samples_detection_log_id', 'retraining_samples', ['detection_log_id'])
