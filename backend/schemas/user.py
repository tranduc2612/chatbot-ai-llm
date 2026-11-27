from datetime import datetime

from pydantic import BaseModel, EmailStr, Field, model_validator

from models.user import UserRole

# Chữ, số và _ . - ; không cho '@' để username không bị nhầm với email khi đăng nhập
USERNAME_PATTERN = r"^[A-Za-z0-9_.-]+$"


class UserBase(BaseModel):
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100, pattern=USERNAME_PATTERN)
    full_name: str | None = Field(default=None, max_length=255)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)


class UserUpdate(BaseModel):
    """User tự sửa thông tin của mình. Đổi mật khẩu phải kèm mật khẩu hiện tại."""

    full_name: str | None = Field(default=None, max_length=255)
    current_password: str | None = Field(default=None, max_length=128)
    new_password: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def _require_current_password(self) -> "UserUpdate":
        if self.new_password is not None and not self.current_password:
            raise ValueError("current_password is required to change password")
        return self


class UserRoleUpdate(BaseModel):
    role: UserRole


class UserStatusUpdate(BaseModel):
    is_active: bool


class UserResponse(UserBase):
    id: int
    role: UserRole
    is_active: bool
    is_verified: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserListResponse(BaseModel):
    total: int
    items: list[UserResponse]
