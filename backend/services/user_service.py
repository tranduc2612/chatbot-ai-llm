from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from core.security import hash_password, verify_password
from models.user import User, UserRole
from schemas.user import UserCreate

# Hash giả để verify khi không tìm thấy user, giúp thời gian phản hồi
# tương đương trường hợp sai mật khẩu (tránh dò xem email có tồn tại không).
_DUMMY_HASH = hash_password("dummy-password-for-timing")


class UserAlreadyExistsError(Exception):
    """Email hoặc username đã được sử dụng."""

    def __init__(self, field: str):
        self.field = field
        super().__init__(f"{field} already registered")


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: int) -> User | None:
        return await self.db.get(User, user_id)

    async def get_by_email(self, email: str) -> User | None:
        result = await self.db.execute(select(User).where(User.email == email.lower()))
        return result.scalar_one_or_none()

    async def get_by_username(self, username: str) -> User | None:
        result = await self.db.execute(select(User).where(User.username == username))
        return result.scalar_one_or_none()

    async def get_by_email_or_username(self, identifier: str) -> User | None:
        result = await self.db.execute(
            select(User).where(
                or_(User.email == identifier.lower(), User.username == identifier)
            )
        )
        return result.scalar_one_or_none()

    async def create(self, data: UserCreate) -> User:
        email = data.email.lower()
        if await self.get_by_email(email):
            raise UserAlreadyExistsError("email")
        if await self.get_by_username(data.username):
            raise UserAlreadyExistsError("username")

        user = User(
            email=email,
            username=data.username,
            full_name=data.full_name,
            hashed_password=hash_password(data.password),
        )
        self.db.add(user)
        try:
            await self.db.commit()
        except IntegrityError:
            # Hai request đăng ký cùng lúc vượt qua bước kiểm tra ở trên
            await self.db.rollback()
            raise UserAlreadyExistsError("email or username")
        await self.db.refresh(user)
        return user

    async def list_users(
        self, skip: int = 0, limit: int = 20, search: str | None = None
    ) -> tuple[int, list[User]]:
        """Trả về (tổng số user khớp điều kiện, danh sách trang hiện tại)."""
        query = select(User)
        if search:
            # Escape ký tự wildcard của LIKE để tìm đúng nghĩa đen "%", "_".
            # Dùng "!" làm ký tự escape (tránh "\" vốn là escape trong chuỗi MySQL).
            escaped = search.replace("!", "!!").replace("%", "!%").replace("_", "!_")
            pattern = f"%{escaped}%"
            query = query.where(
                or_(
                    User.email.ilike(pattern, escape="!"),
                    User.username.ilike(pattern, escape="!"),
                )
            )

        total = await self.db.scalar(select(func.count()).select_from(query.subquery()))
        result = await self.db.execute(query.order_by(User.id).offset(skip).limit(limit))
        return total or 0, list(result.scalars().all())

    async def count_active_admins(self) -> int:
        return await self.db.scalar(
            select(func.count()).where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        ) or 0

    async def update_profile(
        self, user: User, full_name: str | None = None, new_password: str | None = None
    ) -> User:
        if full_name is not None:
            user.full_name = full_name
        if new_password is not None:
            user.hashed_password = hash_password(new_password)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_role(self, user: User, role: UserRole) -> User:
        user.role = role
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def set_active(self, user: User, is_active: bool) -> User:
        user.is_active = is_active
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def authenticate(self, identifier: str, password: str) -> User | None:
        """Đăng nhập bằng email hoặc username. Trả về User nếu đúng mật khẩu."""
        user = await self.get_by_email_or_username(identifier)
        if user is None:
            verify_password(password, _DUMMY_HASH)
            return None
        if not verify_password(password, user.hashed_password):
            return None
        return user
