"""Chuẩn bị database khi khởi động: tạo database nếu chưa có."""

import logging
import re

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from core.config import settings

logger = logging.getLogger(__name__)

_DB_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_$]+$")


async def ensure_database_exists() -> None:
    """Kết nối vào MySQL server (không chọn database) và tạo database trong
    DATABASE_URL nếu chưa tồn tại. Đã có thì không làm gì."""
    if not settings.DATABASE_URL:
        raise RuntimeError("DATABASE_URL is not set")

    url = make_url(settings.DATABASE_URL)
    if not url.drivername.startswith("mysql"):
        return  # chỉ hỗ trợ tự tạo database cho MySQL

    db_name = url.database
    if not db_name:
        raise RuntimeError("DATABASE_URL must include a database name")
    if not _DB_NAME_PATTERN.match(db_name):
        raise RuntimeError(f"Invalid database name: {db_name!r}")

    # information_schema luôn tồn tại trên MySQL → dùng để kết nối khi DB đích chưa có
    server_engine = create_async_engine(
        url.set(database="information_schema"), isolation_level="AUTOCOMMIT"
    )
    try:
        async with server_engine.connect() as conn:
            exists = await conn.scalar(
                text(
                    "SELECT SCHEMA_NAME FROM information_schema.SCHEMATA "
                    "WHERE SCHEMA_NAME = :name"
                ),
                {"name": db_name},
            )
            if exists:
                logger.info("Database %s already exists", db_name)
                return

            await conn.execute(
                text(
                    f"CREATE DATABASE `{db_name}` "
                    "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
                )
            )
            logger.info("Created database %s", db_name)
    finally:
        await server_engine.dispose()
