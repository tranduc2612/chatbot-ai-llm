"""Dữ liệu khởi tạo chạy lúc khởi động (sau migration)."""

import logging

from sqlalchemy import or_, select

from core.config import settings
from core.database import AsyncSessionLocal
from core.security import hash_password
from models.user import User, UserRole

logger = logging.getLogger(__name__)

_COMMON_PASSWORDS = {
    "123456", "12345678", "123456789", "password", "admin", "admin123",
    "qwerty", "111111", "abc123", "1234567890",
}


def _is_weak(password: str) -> bool:
    return len(password) < 8 or password.lower() in _COMMON_PASSWORDS


async def ensure_admin_user() -> None:
    """Tạo tài khoản admin từ ADMIN_* trong .env nếu chưa có.

    Đã có thì không sửa gì (không đè mật khẩu đã đổi sau này).
    """
    if not settings.ADMIN_PASSWORD:
        logger.warning("ADMIN_PASSWORD is not set; skipping default admin creation")
        return

    username = settings.ADMIN_USERNAME
    email = settings.ADMIN_EMAIL.lower()

    async with AsyncSessionLocal() as db:
        existing = (
            await db.execute(
                select(User).where(or_(User.username == username, User.email == email))
            )
        ).scalars().all()

        if existing:
            for user in existing:
                if user.role != UserRole.ADMIN:
                    # Không tự nâng quyền: tài khoản này có thể do người khác đăng ký
                    logger.error(
                        "User %r (id=%s) uses the admin username/email but is not ADMIN; "
                        "not changing it. Fix manually or change ADMIN_USERNAME/ADMIN_EMAIL.",
                        user.username, user.id,
                    )
            logger.info("Admin user %r already exists", username)
            return

        db.add(
            User(
                username=username,
                email=email,
                full_name="Administrator",
                hashed_password=hash_password(settings.ADMIN_PASSWORD),
                role=UserRole.ADMIN,
                is_active=True,
                is_verified=True,
            )
        )
        await db.commit()
        logger.info("Created admin user %r", username)

    if _is_weak(settings.ADMIN_PASSWORD):
        logger.warning(
            "Admin user %r was created with a weak password. Change it before deploying.",
            username,
        )
