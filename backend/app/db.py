# PostgreSQL 엔진 생성, 연결 확인, 요청별 SQLAlchemy 세션 공급.
# 엔진은 재사용하고 세션은 요청 범위에서 닫으며 실제 변경 확정(commit)은 호출하는 기능이 담당한다.
from functools import lru_cache
import time
from sqlalchemy import create_engine, text, event, exc
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from fastapi import HTTPException
from .config import settings


# PostgreSQL psycopg URL을 검사하고 pooler 방식에 맞는 연결 설정으로 재사용 엔진을 만든다.
# 엔진과 연결 풀을 요청마다 새로 만들지 않도록 최초 생성 결과를 재사용한다.
@lru_cache
def get_engine():
    if not settings.database_url:
        raise RuntimeError('DATABASE_URL is not configured')
    if not settings.database_url.startswith('postgresql+psycopg://'):
        raise RuntimeError('PostgreSQL psycopg URL is required')
    connect_args = {'connect_timeout': settings.db_connect_timeout}
    # transaction pooler(6543)는 연결을 트랜잭션마다 바꾸므로 앱 풀과 prepared statement를 쓰지 않는다.
    if settings.db_pool_mode == 'transaction':
        return create_engine(settings.database_url, poolclass=NullPool,
                             connect_args={**connect_args, 'prepare_threshold': None})
    # session pooler(5432)·로컬 DB는 작은 풀을 재사용한다. 운영 서버와 DB가 멀어 왕복 1번이 비싸므로
    # 요청마다 pre-ping하지 않고, 30초 넘게 쉰 연결만 꺼낼 때 확인해 끊긴 연결을 걸러낸다.
    engine = create_engine(settings.database_url, pool_size=2, max_overflow=3, connect_args=connect_args)
    event.listen(engine, 'checkin', _mark_idle)
    event.listen(engine, 'checkout', _ping_if_idle)
    return engine


IDLE_PING_SECONDS = 30


def _mark_idle(dbapi_connection, record):
    record.info['idle_since'] = time.monotonic()


def _ping_if_idle(dbapi_connection, record, proxy):
    idle_since = record.info.get('idle_since')
    if idle_since is None or time.monotonic() - idle_since < IDLE_PING_SECONDS:
        return
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute('SELECT 1')
        cursor.close()
    except Exception as error:
        # 풀이 이 연결을 버리고 새 연결로 다시 꺼낸다(SQLAlchemy 비관적 연결 확인 방식).
        raise exc.DisconnectionError() from error


# DB 연결을 열어 SELECT 1로 실제 응답 여부를 확인한 뒤 연결을 닫는다.
def check_database():
    with get_engine().connect() as connection:
        connection.execute(text('SELECT 1'))


# 요청별 ORM 세션을 yield하고 요청 처리가 끝나면 세션을 닫는다.
def get_db():
    try:
        engine = get_engine()
    except RuntimeError:
        raise HTTPException(503, 'PostgreSQL 설정이 필요합니다.')
    with Session(engine) as session:
        yield session
