# PostgreSQL 엔진 생성, 연결 확인, 요청별 SQLAlchemy 세션 공급.
# 엔진은 재사용하고 세션은 요청 범위에서 닫으며 실제 변경 확정(commit)은 호출하는 기능이 담당한다.
from functools import lru_cache
from sqlalchemy import create_engine, text
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
    # session pooler(5432)·로컬 DB는 작은 풀을 재사용하고 pool_pre_ping으로 끊긴 연결을 걸러낸다.
    return create_engine(settings.database_url, pool_pre_ping=True, pool_size=2, max_overflow=3,
                         connect_args=connect_args)


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
