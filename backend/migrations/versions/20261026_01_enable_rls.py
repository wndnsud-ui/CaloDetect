"""Supabase 공유 DB: public 스키마 테이블에 RLS를 켠다 (정책 없음).

백엔드는 테이블 소유자(postgres)로 직접 접속하므로 영향이 없고, Supabase Data API(anon key) 노출만 막는다.
SQLite 테스트에서는 실행하지 않는다.
"""
from alembic import op
import sqlalchemy as sa

revision = '20261026_01'
down_revision = '20261022_02'
branch_labels = None
depends_on = None


# public 스키마의 일반 테이블 이름(alembic_version 포함)을 조회한다.
def _public_tables(bind):
    rows = bind.execute(sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename"))
    return [row[0] for row in rows]


def _set_rls(action):
    bind = op.get_bind()
    if bind.dialect.name != 'postgresql':
        return
    preparer = bind.dialect.identifier_preparer
    for table in _public_tables(bind):
        op.execute(f'ALTER TABLE public.{preparer.quote(table)} {action} ROW LEVEL SECURITY')


def upgrade():
    _set_rls('ENABLE')


def downgrade():
    _set_rls('DISABLE')
