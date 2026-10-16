"""승인된 로컬 20261007_03 → v5 전환. 기본은 검사만, 전체 작업은 한 트랜잭션.

빈 구형 테이블을 별도 schema로 보존한다. 임의 stamp, 테이블 삭제, 데이터 재생성은 하지 않는다.
다른 DB 상태나 운영 환경에서는 중단한다. 실행 전 pg_dump 백업 필수.
"""
import argparse
import importlib
from pathlib import Path
from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import MetaData, inspect, text
from backend.app.main import app  # 모든 기존 ORM metadata 등록
from backend.app.models import Base
from backend.app.config import settings
from backend.app.db import get_engine

LEGACY = ('community_posts', 'community_reactions', 'community_comments')
NEW = {'community_posts', 'community_reactions', 'community_post_images', 'point_transactions'}
ARCHIVE = 'community_legacy_20261016'


def fingerprint(connection, tables, schema='public'):
    # 값은 출력하지 않고 서버에서 계산한 hash·건수로만 전후 동일성을 확인한다.
    result = {}
    for name in sorted(tables):
        if not name.replace('_', '').isalnum():
            raise RuntimeError('Unexpected table identifier')
        result[name] = tuple(connection.execute(text(
            f'SELECT count(*), md5(coalesce(string_agg(h, \'\' ORDER BY h), \'\')) '
            f'FROM (SELECT md5(row_to_json(t)::text) h FROM "{schema}"."{name}" t) s')).one())
    return result


def apply(backup, execute=False):
    if settings.app_env != 'development':
        raise RuntimeError('Only the authorized local development DB is supported')
    if execute:
        path = Path(backup).resolve()
        with path.open('rb') as stream:
            if stream.read(5) != b'PGDMP' or path.stat().st_size < 1024:
                raise RuntimeError('Validated pg_dump custom archive is required')
    baseline = MetaData()
    for name, table in Base.metadata.tables.items():
        if name not in NEW:
            table.to_metadata(baseline)
    with get_engine().begin() as connection:
        if connection.get_isolation_level() != 'READ COMMITTED':
            raise RuntimeError('READ COMMITTED required')
        connection.execute(text("SET LOCAL lock_timeout = '5s'"))
        connection.execute(text("SET LOCAL statement_timeout = '60s'"))
        connection.execute(text('SELECT pg_advisory_xact_lock(20261016, 1)'))
        revision = connection.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
        if revision != ['20261007_03']:
            raise RuntimeError('Expected the specifically audited 20261007_03 revision; no changes made')
        inspector = inspect(connection)
        if ARCHIVE in inspector.get_schema_names():
            raise RuntimeError('Archive schema already exists; no overwrite permitted')
        tables = set(inspector.get_table_names(schema='public'))
        if not set(LEGACY).issubset(tables) or (NEW - set(LEGACY)) & tables:
            raise RuntimeError('Unexpected community table state')
        # 모든 관련 테이블의 쓰기를 막은 상태로 대조·보관·적용·데이터 검증까지 수행한다.
        connection.execute(text('LOCK TABLE '+', '.join(f'public."{name}"' for name in sorted(tables))+' IN SHARE ROW EXCLUSIVE MODE'))
        if any(count for count, _ in fingerprint(connection, LEGACY).values()):
            raise RuntimeError('Legacy tables are no longer empty; separate review required')
        context = MigrationContext.configure(connection, opts={
            'include_object': lambda obj, name, kind, reflected, other:
                name not in NEW | set(LEGACY) if kind == 'table' else True})
        if compare_metadata(context, baseline):
            raise RuntimeError('Existing schema differs from the audited 20261015_02 baseline')
        protected = tables - set(LEGACY) - {'alembic_version'}
        before = fingerprint(connection, protected)
        legacy_before = fingerprint(connection, LEGACY)
        print('Preflight OK: exact baseline schema, empty legacy tables, READ COMMITTED')
        print('Existing counts:', {k: before[k][0] for k in ('users', 'meals', 'meal_items')})
        if not execute:
            print('CHECK ONLY: no tables or revision changed')
            return
        connection.execute(text(f'CREATE SCHEMA "{ARCHIVE}"'))
        for name in LEGACY:
            connection.execute(text(f'ALTER TABLE public."{name}" SET SCHEMA "{ARCHIVE}"'))
        migration = importlib.import_module('backend.migrations.versions.20261016_01_community')
        if migration.down_revision != '20261015_02':
            raise RuntimeError('Unexpected migration parent')
        # 실제 스키마를 기준 revision과 대조한 뒤 그 후속 migration만 적용한다.
        with Operations.context(context):
            migration.upgrade()
        updated = connection.execute(text(
            "UPDATE public.alembic_version SET version_num='20261016_01' WHERE version_num='20261007_03'"))
        if updated.rowcount != 1:
            raise RuntimeError('Revision changed concurrently')
        if fingerprint(connection, protected) != before:
            raise RuntimeError('Existing data changed; rolling back entire transition')
        if fingerprint(connection, LEGACY, ARCHIVE) != legacy_before:
            raise RuntimeError('Archived data mismatch; rolling back entire transition')
        final_context = MigrationContext.configure(connection)
        if compare_metadata(final_context, Base.metadata):
            raise RuntimeError('Final public schema mismatch; rolling back entire transition')
        print('Applied v5; revision 20261016_01. Existing row fingerprints unchanged.')
        print('Legacy tables preserved in', ARCHIVE)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--backup', help='Validated private pg_dump custom archive path')
    args = parser.parse_args()
    if args.apply and not args.backup:
        parser.error('--apply requires --backup')
    apply(args.backup, args.apply)
