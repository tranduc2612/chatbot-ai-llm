from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from core.database import get_db
from core.security import decode_access_token
from models.user import User, UserRole
from services.user_service import UserService

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_access_token(token)
    if user_id is None:
        raise credentials_exception

    service = UserService(db)
    user = await service.get_by_id(int(user_id))
    if user is None:
        raise credentials_exception
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")
    return current_user


CurrentUser = Annotated[User, Depends(get_current_user)]
# Mọi user đã đăng nhập và đang hoạt động (role nào cũng được)
LoggedInUser = Annotated[User, Depends(get_current_active_user)]


def require_roles(*roles: UserRole):
    """Dependency: chỉ cho user đang hoạt động có một trong các role chỉ định.

    Thường dùng qua alias AdminUser bên dưới.
    """
    allowed = set(roles)

    async def checker(current_user: LoggedInUser) -> User:
        if current_user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not enough permissions",
            )
        return current_user

    return checker


# Chỉ ADMIN
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]
