from functools import lru_cache
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
from fastapi import HTTPException
from .config import settings


@lru_cache
def get_engine():
    if not settings.database_url:
        raise RuntimeError('DATABASE_URL is not configured')
    if not settings.database_url.startswith('postgresql+psycopg://'):
        raise RuntimeError('PostgreSQL psycopg URL is required')
    return create_engine(settings.database_url, pool_pre_ping=True,
                         connect_args={'connect_timeout': 3})


def check_database():
    with get_engine().connect() as connection:
        connection.execute(text('SELECT 1'))


def get_db():
    try:
        engine = get_engine()
    except RuntimeError:
        raise HTTPException(503, 'PostgreSQL 설정이 필요합니다.')
    with Session(engine) as session:
        yield session
