from alembic import context
from backend.app.db import get_engine
from backend.app.models import Base

if context.is_offline_mode():
    raise RuntimeError('Run migrations online with configured DATABASE_URL.')
else:
    with get_engine().connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata)
        with context.begin_transaction():
            context.run_migrations()
