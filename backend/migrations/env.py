# Alembic 실행 환경. 기존 ORM 메타데이터와 DB 설정을 연결해 migration을 적용한다.
# 테이블 변경 이력 자체는 versions의 revision 파일에 정의된다.
from alembic import context
from backend.app.db import get_engine
from backend.app.models import Base

# 현재 migration은 실제 DATABASE_URL 연결에서만 실행하도록 offline SQL 생성을 거부한다.
if context.is_offline_mode():
    raise RuntimeError('Run migrations online with configured DATABASE_URL.')
else:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        # Alembic 트랜잭션 범위에서 대기 revision을 실행해 이력과 스키마 적용을 관리한다.
        with context.begin_transaction():
            context.run_migrations()
