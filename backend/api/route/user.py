from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import AdminUser, LoggedInUser
from core.database import get_db
from core.security import verify_password
from models.user import User, UserRole
from schemas.user import (
    UserListResponse,
    UserResponse,
    UserRoleUpdate,
    UserStatusUpdate,
    UserUpdate,
)
from services.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])


# ---------- Mọi user đã đăng nhập ----------
# Lưu ý: route /me phải khai báo trước /{user_id}


@router.patch("/me", response_model=UserResponse)
async def update_me(
    data: UserUpdate,
    current_user: LoggedInUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    if data.new_password is not None and not verify_password(
        data.current_password or "", current_user.hashed_password
    ):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Current password is incorrect")

    return await UserService(db).update_profile(
        current_user, full_name=data.full_name, new_password=data.new_password
    )


# ---------- Chỉ ADMIN ----------


async def _get_user_or_404(service: UserService, user_id: int) -> User:
    user = await service.get_by_id(user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


async def _ensure_not_last_admin(service: UserService, target: User) -> None:
    """Chặn thao tác làm hệ thống không còn admin nào hoạt động."""
    if target.role == UserRole.ADMIN and target.is_active:
        if await service.count_active_admins() <= 1:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cannot remove the last active admin",
            )


@router.get("", response_model=UserListResponse)
async def list_users(
    _: AdminUser,
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    search: str | None = Query(None, max_length=100, description="Tìm theo email hoặc username"),
    db: AsyncSession = Depends(get_db),
) -> UserListResponse:
    total, items = await UserService(db).list_users(skip=skip, limit=limit, search=search)
    return UserListResponse(total=total, items=items)


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, _: AdminUser, db: AsyncSession = Depends(get_db)) -> User:
    return await _get_user_or_404(UserService(db), user_id)


@router.patch("/{user_id}/role", response_model=UserResponse)
async def update_user_role(
    user_id: int,
    data: UserRoleUpdate,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    service = UserService(db)
    target = await _get_user_or_404(service, user_id)

    if target.role == data.role:
        return target
    if data.role != UserRole.ADMIN:  # hạ quyền
        if target.id == admin.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot change your own role")
        await _ensure_not_last_admin(service, target)

    return await service.set_role(target, data.role)


@router.patch("/{user_id}/status", response_model=UserResponse)
async def update_user_status(
    user_id: int,
    data: UserStatusUpdate,
    admin: AdminUser,
    db: AsyncSession = Depends(get_db),
) -> User:
    service = UserService(db)
    target = await _get_user_or_404(service, user_id)

    if target.is_active == data.is_active:
        return target
    if not data.is_active:  # khóa tài khoản
        if target.id == admin.id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="You cannot deactivate yourself")
        await _ensure_not_last_admin(service, target)

    return await service.set_active(target, data.is_active)
