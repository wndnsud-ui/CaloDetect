# TEST-ONLY: 개인 브랜치 한정, 팀 반영 시 Backend Core A 담당 이관.
# 채팅 식사기록 A1: 대화·메시지·첨부·식사 초안 테이블과 meals.chat_attachment_id(nullable) 추가(additive only).
"""Chat record A1: conversations, messages, attachments, meal drafts."""
from alembic import op
import sqlalchemy as sa

revision = "20261015_02"
down_revision = "20261015_01"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('chat_conversations',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('next_sequence', sa.Integer(), nullable=False),
    sa.Column('pending_question', sa.String(length=20), nullable=False),
    sa.Column('pending_payload', sa.JSON(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_chat_conversations_user_id', 'chat_conversations', ['user_id'])
    op.create_table('chat_messages',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('sequence', sa.Integer(), nullable=False),
    sa.Column('author_role', sa.String(length=8), nullable=False),
    sa.Column('kind', sa.String(length=20), nullable=False),
    sa.Column('text', sa.String(length=1000), nullable=False),
    sa.Column('payload', sa.JSON(), nullable=True),
    sa.Column('client_message_id', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('reply_to_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('conversation_id', 'sequence', name='uq_chat_messages_sequence'),
    sa.UniqueConstraint('user_id', 'conversation_id', 'client_message_id', name='uq_chat_messages_client'))
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_table('chat_attachments',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('message_id', sa.String(length=36), nullable=True),
    sa.Column('image_upload_id', sa.String(length=36), nullable=True),
    sa.Column('mime', sa.String(length=40), nullable=False),
    sa.Column('size', sa.Integer(), nullable=False),
    sa.Column('checksum', sa.String(length=64), nullable=False),
    sa.Column('status', sa.String(length=16), nullable=False),
    sa.Column('upload_request_id', sa.String(length=36), nullable=False),
    sa.Column('storage_key', sa.String(length=255), nullable=False),
    sa.Column('analysis_error', sa.String(length=120), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['image_upload_id'], ['image_uploads.id']),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('user_id', 'upload_request_id', name='uq_chat_attachments_request'))
    op.create_index('ix_chat_attachments_user_id', 'chat_attachments', ['user_id'])
    op.create_index('ix_chat_attachments_conversation_id', 'chat_attachments', ['conversation_id'])
    op.add_column('meals', sa.Column('chat_attachment_id', sa.String(length=36), nullable=True))
    op.create_foreign_key('fk_meals_chat_attachment', 'meals', 'chat_attachments', ['chat_attachment_id'], ['id'])
    op.create_table('meal_drafts',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('conversation_id', sa.String(length=36), nullable=False),
    sa.Column('user_id', sa.Integer(), nullable=False),
    sa.Column('attachment_id', sa.String(length=36), nullable=True),
    sa.Column('status', sa.String(length=24), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('meal_date', sa.Date(), nullable=False),
    sa.Column('meal_type', sa.String(length=16), nullable=False),
    sa.Column('pending_question', sa.String(length=20), nullable=False),
    sa.Column('pending_target_id', sa.String(length=36), nullable=True),
    sa.Column('analysis_failed', sa.Boolean(), nullable=False),
    sa.Column('confirmed_meal_id', sa.String(length=36), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("meal_type IN ('breakfast','lunch','dinner','snack')", name='ck_meal_drafts_type'),
    sa.ForeignKeyConstraint(['conversation_id'], ['chat_conversations.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['attachment_id'], ['chat_attachments.id']),
    sa.ForeignKeyConstraint(['confirmed_meal_id'], ['meals.id']),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('confirmed_meal_id'))
    op.create_index('ix_meal_drafts_conversation_id', 'meal_drafts', ['conversation_id'])
    op.create_index('ix_meal_drafts_user_id', 'meal_drafts', ['user_id'])
    op.create_table('meal_draft_items',
    sa.Column('id', sa.String(length=36), nullable=False),
    sa.Column('draft_id', sa.String(length=36), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('source_detection_id', sa.String(length=36), nullable=True),
    sa.Column('food_id', sa.Integer(), nullable=False),
    sa.Column('serving_multiplier', sa.Float(), nullable=False),
    sa.Column('consumption_ratio', sa.Float(), nullable=False),
    sa.Column('nutrition', sa.JSON(), nullable=False),
    sa.Column('confidence', sa.Float(), nullable=True),
    sa.Column('bbox', sa.JSON(), nullable=True),
    sa.CheckConstraint('consumption_ratio >= 0 AND consumption_ratio <= 1', name='ck_draft_items_ratio'),
    sa.CheckConstraint('serving_multiplier = 1', name='ck_draft_items_base'),
    sa.ForeignKeyConstraint(['draft_id'], ['meal_drafts.id'], ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['source_detection_id'], ['detection_logs.id']),
    sa.ForeignKeyConstraint(['food_id'], ['foods.id']),
    sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_meal_draft_items_draft_id', 'meal_draft_items', ['draft_id'])


def downgrade():
    op.drop_index('ix_meal_draft_items_draft_id', table_name='meal_draft_items')
    op.drop_table('meal_draft_items')
    op.drop_index('ix_meal_drafts_user_id', table_name='meal_drafts')
    op.drop_index('ix_meal_drafts_conversation_id', table_name='meal_drafts')
    op.drop_table('meal_drafts')
    op.drop_constraint('fk_meals_chat_attachment', 'meals', type_='foreignkey')
    op.drop_column('meals', 'chat_attachment_id')
    op.drop_index('ix_chat_attachments_conversation_id', table_name='chat_attachments')
    op.drop_index('ix_chat_attachments_user_id', table_name='chat_attachments')
    op.drop_table('chat_attachments')
    op.drop_index('ix_chat_messages_user_id', table_name='chat_messages')
    op.drop_index('ix_chat_messages_conversation_id', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('ix_chat_conversations_user_id', table_name='chat_conversations')
    op.drop_table('chat_conversations')
