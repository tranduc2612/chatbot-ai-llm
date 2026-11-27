# Import mọi model ở đây để Base.metadata biết đủ các bảng
# (Alembic autogenerate và lúc khởi động đều dựa vào đây).
from models.user import User, UserRole  # noqa: F401
