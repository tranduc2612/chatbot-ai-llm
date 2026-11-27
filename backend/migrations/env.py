import asyncio
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

from core.config import settings
from core.database import Base
import models  # noqa: F401  # nạp tất cả model vào Base.metadata

config = context.config

# Khi chạy từ CLI (`alembic ...`) thì cấu hình logging theo alembic.ini.
# Khi app gọi lúc khởi động (core/migrations.py) thì bỏ qua để không ghi đè
# logging của uvicorn.
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata

# Lấy URL từ settings (.env), không ghi mật khẩu vào alembic.ini
DATABASE_URL = settings.DATABASE_URL


def run_migrations_offline() -> None:
    """Sinh SQL ra màn hình thay vì chạy (`alembic upgrade head --sql`)."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = create_async_engine(DATABASE_URL, poolclass=pool.NullPool)

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
        # SQLAlchemy 2.x rollback khi đóng kết nối nếu chưa commit → phải commit
        # để dòng version trong bảng alembic_version được lưu lại.
        await connection.commit()

    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
