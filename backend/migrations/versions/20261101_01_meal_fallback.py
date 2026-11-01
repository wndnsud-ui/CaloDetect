"""Photo-only and editable meals; external catalog retains original model IDs.

Apply to shared Supabase only through the designated migration owner after merge.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261101_01'
down_revision = '20261031_01'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('nutrition_foods', sa.Column('id', sa.String(80), primary_key=True),
                    sa.Column('name', sa.String(200), nullable=False),
                    sa.Column('serving_amount', sa.Float(), nullable=False),
                    sa.Column('serving_unit', sa.String(8), nullable=False, server_default='g'),
                    sa.Column('nutrition', sa.JSON(), nullable=False),
                    sa.Column('source', sa.String(255), nullable=False))
    op.create_index('ix_nutrition_foods_name', 'nutrition_foods', ['name'])
    with op.batch_alter_table('meals') as batch:
        batch.add_column(sa.Column('analysis_status', sa.String(16), nullable=False, server_default='analyzed'))
        batch.add_column(sa.Column('image_upload_id', sa.String(36)))
        batch.add_column(sa.Column('photo_override', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.create_foreign_key('fk_meal_image_upload', 'image_uploads', ['image_upload_id'], ['id'])
        batch.add_column(sa.Column('meal_time', sa.String(5)))
        batch.add_column(sa.Column('version', sa.Integer(), nullable=False, server_default='1'))
        batch.create_check_constraint('ck_meal_analysis_status', "analysis_status IN ('pending','analyzed','skipped','failed')")
    with op.batch_alter_table('meal_items') as batch:
        batch.alter_column('food_id', existing_type=sa.Integer(), nullable=True)
        batch.add_column(sa.Column('reference_food_id', sa.String(80)))
        batch.create_foreign_key('fk_meal_item_reference', 'nutrition_foods', ['reference_food_id'], ['id'])
        batch.add_column(sa.Column('source', sa.String(16), nullable=False, server_default='ai'))
        batch.add_column(sa.Column('ai_confidence', sa.Float()))
        batch.add_column(sa.Column('is_edited', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('is_llm_estimated', sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column('amount', sa.Float(), nullable=False, server_default='1'))
        batch.add_column(sa.Column('amount_unit', sa.String(16), nullable=False, server_default='serving'))
        batch.create_check_constraint('ck_meal_item_source', "source IN ('ai','search','manual')")
        batch.create_check_constraint('ck_meal_item_amount', "amount > 0 AND amount_unit IN ('g','ml','serving')")
        batch.create_check_constraint('ck_meal_item_serving_multiplier', 'serving_multiplier > 0')
        batch.create_check_constraint('ck_meal_item_ai_confidence', 'ai_confidence IS NULL OR (ai_confidence >= 0 AND ai_confidence <= 1)')
    op.execute("UPDATE meal_items SET source = CASE WHEN detection_log_id IS NULL THEN 'search' ELSE 'ai' END, ai_confidence = confidence, amount = serving_multiplier")
    if op.get_bind().dialect.name == 'postgresql':
        op.execute('ALTER TABLE public.nutrition_foods ENABLE ROW LEVEL SECURITY')


def downgrade():
    # New free-form meals cannot be losslessly represented by the old mandatory food FK.
    raise RuntimeError('Export new meal records and plan a data-preserving rollback before downgrade.')
