from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from api.deps import LoggedInUser
from core.database import get_db
from core.security import create_access_token, create_refresh_token, decode_refresh_token
from models.user import User
from schemas.auth import RefreshTokenRequest, Token
from schemas.user import UserCreate, UserResponse
from services.user_service import UserAlreadyExistsError, UserService

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user: User) -> Token:
    return Token(
        access_token=create_access_token(subject=user.id),
        refresh_token=create_refresh_token(subject=user.id),
    )


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: AsyncSession = Depends(get_db)) -> User:
    service = UserService(db)
    try:
        return await service.create(data)
    except UserAlreadyExistsError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"{e.field.capitalize()} already registered",
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
) -> Token:
    """Đăng nhập bằng email hoặc username (trường `username` của form)."""
    service = UserService(db)
    user = await service.authenticate(form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username/email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Inactive user")

    return _issue_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh_token(data: RefreshTokenRequest, db: AsyncSession = Depends(get_db)) -> Token:
    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_refresh_token(data.refresh_token)
    if user_id is None:
        raise invalid

    user = await UserService(db).get_by_id(int(user_id))
    if user is None or not user.is_active:
        raise invalid

    return _issue_tokens(user)


@router.get("/me", response_model=UserResponse)
async def read_me(current_user: LoggedInUser) -> User:
    return current_user
