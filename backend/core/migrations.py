"""Tự động đưa database lên version mới nhất (Alembic head) khi khởi động."""

import asyncio
import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import inspect
from sqlalchemy.engine import Connection

from core.database import engine

logger = logging.getLogger(__name__)

ALEMBIC_INI = Path(__file__).resolve().parent.parent / "alembic.ini"


def _alembic_config() -> Config:
    cfg = Config(str(ALEMBIC_INI))
    cfg.attributes["configure_logger"] = False  # giữ nguyên logging của uvicorn
    return cfg


def _read_db_state(conn: Connection) -> tuple[str | None, bool]:
    """Trả về (version hiện tại, DB có bảng ứng dụng nào ngoài alembic_version không)."""
    current = MigrationContext.configure(conn).get_current_revision()
    app_tables = [t for t in inspect(conn).get_table_names() if t != "alembic_version"]
    return current, bool(app_tables)


async def run_migrations() -> None:
    cfg = _alembic_config()
    script = ScriptDirectory.from_config(cfg)

    heads = script.get_heads()
    if len(heads) > 1:
        raise RuntimeError(
            f"Multiple Alembic heads {heads}; run `alembic merge heads` first"
        )
    head = heads[0] if heads else None

    async with engine.connect() as conn:
        current, has_tables = await conn.run_sync(_read_db_state)

    if current == head:
        logger.info("Database is up to date (revision %s)", current)
        return

    if current is None and has_tables:
        # Bảng được tạo ngoài Alembic (vd. create_all) → upgrade sẽ lỗi "table exists"
        raise RuntimeError(
            "Database has tables but no Alembic version. Back up the data, then "
            "either drop those tables or run `alembic stamp <revision>` to mark "
            "the matching version."
        )

    logger.info("Upgrading database: %s -> %s", current or "<empty>", head)
    # env.py tự gọi asyncio.run(), nên phải chạy ở thread riêng (không có event loop)
    await asyncio.to_thread(command.upgrade, cfg, "head")
    logger.info("Database upgraded to %s", head)
