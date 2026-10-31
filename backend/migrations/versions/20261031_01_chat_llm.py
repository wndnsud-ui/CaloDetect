# 칼로티 코치 LLM(챗봇 업무지시서 v1.2): 외부 AI 전송 고지 동의·하루 질문 횟수 테이블 추가(additive only).
"""Calo-T Coach LLM: consent and daily usage tables."""
from alembic import op
import sqlalchemy as sa

revision = '20261031_01'
down_revision = '20261027_01'
branch_labels = None
depends_on = None

TABLES = ('chat_llm_consents', 'chat_llm_usage')


def upgrade():
    op.create_table('chat_llm_consents',
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('notice_text', sa.String(length=300), nullable=False),
    sa.Column('consented_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('user_id'))
    op.create_table('chat_llm_usage',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('day', sa.Date(), nullable=False),
    sa.Column('count', sa.Integer(), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'day', name='uq_chat_llm_usage_day'))
    op.create_index('ix_chat_llm_usage_user_id', 'chat_llm_usage', ['user_id'])
    # 20261026_01과 같이 Supabase Data API 노출을 막는다(정책 없음). SQLite에서는 건너뛴다.
    if op.get_bind().dialect.name == 'postgresql':
        for table in TABLES:
            op.execute(f'ALTER TABLE public.{table} ENABLE ROW LEVEL SECURITY')


def downgrade():
    op.drop_index('ix_chat_llm_usage_user_id', table_name='chat_llm_usage')
    op.drop_table('chat_llm_usage')
    op.drop_table('chat_llm_consents')
