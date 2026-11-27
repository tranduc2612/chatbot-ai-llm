# chatbot-ai-llm

Chatbot LLM giai đoạn đầu: backend FastAPI (Python ≥3.12) gọi LLM qua LangChain, có đăng ký/đăng nhập JWT, phân quyền 2 role (admin/user), MySQL + Alembic. Frontend chưa có (`frontend/index.js` trống).

## Chạy backend

- Quản lý dependency bằng `uv` với `backend/pyproject.toml` (không còn `requirements.txt`). Thêm thư viện: `uv add <pkg>`.
- Code dùng import tuyệt đối tính từ `backend/` (vd. `from core.config import settings`), nên mọi lệnh chạy từ thư mục `backend/`: `uv run fastapi dev main.py`.
- Cấu hình qua `backend/.env` (mẫu ở `.env.example`): `DATABASE_URL=mysql+aiomysql://user:pass@localhost:3306/llm_backend`, `CF_ACCOUNT_ID`, `CF_API_TOKEN`, `SECRET_KEY`, `ADMIN_USERNAME`/`ADMIN_EMAIL`/`ADMIN_PASSWORD`... Không ghi mật khẩu/secret làm giá trị mặc định trong `core/config.py` hay trong file được commit.
- Docs: `/api/v1/docs` (nút Authorize dùng được với `/auth/login`).
- MySQL 8 cần gói `cryptography` (đã có) cho `caching_sha2_password`.

## Khởi động & database

`lifespan` trong `main.py` chạy trước khi nhận request; lỗi ở đây sẽ dừng server:

1. `core/db_bootstrap.py` – `ensure_database_exists()`: kết nối qua `information_schema`, tạo database trong `DATABASE_URL` (utf8mb4) nếu chưa có. Chỉ áp dụng cho MySQL.
2. `core/migrations.py` – `run_migrations()`: so version trong `alembic_version` với head.
   - bằng head → bỏ qua; cũ hơn / DB rỗng → `alembic upgrade head` (chạy trong thread vì `env.py` tự gọi `asyncio.run`).
   - có bảng nhưng không có version (bảng tạo ngoài Alembic) → raise, cần drop bảng hoặc `alembic stamp`.
   - nhiều head → raise, cần `alembic merge heads`.
3. `core/seed.py` – `ensure_admin_user()`: tạo admin từ `ADMIN_*` nếu chưa có user trùng username/email (role ADMIN, is_verified). Đã có thì không sửa (không đè mật khẩu); trùng tên nhưng role USER thì chỉ log lỗi, **không tự nâng quyền**. `ADMIN_PASSWORD` trống → bỏ qua. Mật khẩu yếu → log cảnh báo.

Schema chỉ quản lý bằng Alembic — **không dùng `Base.metadata.create_all`** (đã xóa `init_db`).

### Alembic

- `backend/alembic.ini` (`sqlalchemy.url` để trống) + `backend/migrations/env.py` (async, lấy URL từ `settings`, `target_metadata = Base.metadata`, `compare_type=True`, có `await connection.commit()` — thiếu thì version không được lưu).
- Model mới phải được import trong `models/__init__.py` để autogenerate thấy.
- Sửa model → `uv run alembic revision --autogenerate -m "mo ta"` → đọc lại file sinh ra trong `migrations/versions/` → khởi động server (tự upgrade) hoặc `uv run alembic upgrade head`.
- Đổi giá trị enum / chuyển đổi dữ liệu: viết tay migration (cập nhật dữ liệu trước rồi mới `alter_column`), xem migration bỏ moderator làm mẫu.
- Khác: `uv run alembic current`, `uv run alembic check`, `uv run alembic downgrade -1`.
- Migration hiện có: `ceb97deb50de` create users table → `29a43c8fdacf` remove moderator role (head).

## Phân quyền

- Chỉ 2 role: `UserRole.ADMIN` / `UserRole.USER` (MySQL lưu tên enum `ADMIN`/`USER`, API trả `admin`/`user`). Đã bỏ moderator.
- Dependency trong `api/deps.py`:
  - `LoggedInUser` – mọi user đã đăng nhập và đang hoạt động (401 nếu thiếu/sai token, 403 nếu bị khóa).
  - `AdminUser` – chỉ ADMIN (403 `Not enough permissions`).
  - `require_roles(*roles)` – nền của `AdminUser`, dùng khi cần tổ hợp khác.
  - `CurrentUser` – đã đăng nhập, không kiểm tra is_active (ít dùng).
- Role/is_active đọc lại từ DB mỗi request → đổi quyền/khóa có hiệu lực ngay, kể cả với token cũ.
- Admin mặc định: username `ADMIN_USERNAME` (dev: `admin`), mật khẩu lấy từ `ADMIN_PASSWORD` trong `.env`. Bản dev đang dùng mật khẩu yếu — phải đổi trước khi deploy; đổi `.env` không ảnh hưởng tài khoản đã tạo, dùng `PATCH /users/me`.

## Cấu trúc (`backend/`)

- `main.py` – FastAPI app, `lifespan` (tạo DB → migrate → seed admin), gắn `api_router` với prefix `settings.API_PREFIX` (`/api/v1`).
- `api/main.py` – gom router `chat_bot`, `auth`, `user`.
- `api/deps.py` – xem phần Phân quyền.
- `api/route/auth.py` – `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/me`.
- `api/route/user.py` – `/users` (quản lý user cho admin) và `/users/me`. Route `/me` phải khai báo trước `/{user_id}`.
- `api/route/chat_bot.py` – `GET /chat-bot/send?message=...` → `llm_service.generate_response` → `ChatResponse` (chưa yêu cầu đăng nhập).
- `core/config.py` – `Settings` (pydantic-settings, đọc `.env`), singleton `settings`.
- `core/database.py` – async engine, `AsyncSessionLocal`, `Base`, `get_db`, `close_db`.
- `core/security.py` – hash mật khẩu (pwdlib: Argon2 hash mới, Bcrypt để verify hash cũ); JWT (PyJWT) có claim `type` = `access`/`refresh`; `create_access_token`, `create_refresh_token`, `decode_access_token`, `decode_refresh_token` (trả `None` nếu sai loại/hết hạn).
- `core/db_bootstrap.py`, `core/migrations.py`, `core/seed.py` – xem phần Khởi động.
- `models/user.py` – bảng `users` (email unique, username unique, hashed_password, role enum ADMIN/USER, is_active, is_verified, timestamps).
- `schemas/auth.py` – `Token {access_token, refresh_token, token_type}`, `RefreshTokenRequest`.
- `schemas/user.py` – `UserCreate` (username `^[A-Za-z0-9_.-]+$` 3–100 ký tự, không có `@`; password 8–128), `UserUpdate` (`full_name`, `current_password`, `new_password` — đổi mật khẩu bắt buộc có mật khẩu cũ), `UserRoleUpdate`, `UserStatusUpdate`, `UserResponse` (có role, is_verified; không bao giờ trả `hashed_password`), `UserListResponse {total, items}`.
- `services/user_service.py` – `UserService(db)`: `get_by_id`, `get_by_email` (lowercase), `get_by_username`, `get_by_email_or_username`, `create` (raise `UserAlreadyExistsError(field)`, bắt cả `IntegrityError`), `authenticate` (email hoặc username; verify hash giả khi không có user để chống dò email qua thời gian), `list_users(skip, limit, search)`, `count_active_admins`, `update_profile`, `set_role`, `set_active`.
- `services/llm_service.py` – `LLMService` chọn provider theo `LLM_PROVIDER`:
  - `cloudflare`: `ChatOpenAI` với base_url `https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/ai/v1`, model `CF_MODEL` (mặc định `@cf/qwen/qwen3.8-27b`).
  - `ollama`: `ChatOllama` (`OLLAMA_BASE_URL`, `OLLAMA_MODEL`).
  - Singleton `llm_service` khởi tạo lúc import → thiếu `CF_ACCOUNT_ID`/`CF_API_TOKEN` thì app không khởi động.
- Trống: `api/security.py`, `models/chat.py`.

## API (prefix `/api/v1`)

### Auth (`/auth`)

| Endpoint | Input | Thành công | Lỗi |
|---|---|---|---|
| `POST /register` | JSON `UserCreate` | 201 `UserResponse` (role luôn `user`) | 409 trùng email/username, 422 |
| `POST /login` | form OAuth2 `username` (email hoặc username), `password` | 200 `Token` | 401 sai, 403 bị khóa |
| `POST /refresh` | JSON `{refresh_token}` | 200 `Token` mới | 401 token sai/hết hạn/user bị khóa |
| `GET /me` | Bearer access token | 200 `UserResponse` | 401 |

### Users (`/users`)

| Endpoint | Quyền | Input | Lỗi đặc thù |
|---|---|---|---|
| `PATCH /me` | LoggedInUser | JSON `UserUpdate` | 400 sai mật khẩu cũ, 422 thiếu mật khẩu cũ / mật khẩu mới < 8 |
| `GET /` | AdminUser | `skip` (≥0), `limit` (1–100, mặc định 20), `search` (email/username) | — |
| `GET /{id}` | AdminUser | — | 404 |
| `PATCH /{id}/role` | AdminUser | JSON `{role: "admin"\|"user"}` | 400 tự đổi role mình, 409 hạ admin hoạt động cuối cùng, 422 role khác |
| `PATCH /{id}/status` | AdminUser | JSON `{is_active: bool}` | 400 tự khóa mình, 409 khóa admin hoạt động cuối cùng |

## Kiểm thử

- Chưa có test suite. Đã kiểm tra thủ công bằng `fastapi.testclient` (SQLite tạm: `uv run --with aiosqlite ...`, override `get_db`, không dùng `with TestClient` để bỏ qua lifespan MySQL) và với MySQL thật qua server chạy thật (`uv run uvicorn main:app --port 8765`).
- Trên Windows/Git Bash, curl làm hỏng tiếng Việt trong tham số dòng lệnh → test dữ liệu Unicode bằng Python/httpx hoặc Postman.

## Trạng thái hiện tại (2026-11-27)

- Đăng ký/đăng nhập/refresh/me, phân quyền admin/user, quản lý user hoạt động trên MySQL (DB ở revision `29a43c8fdacf`).
- Chat một lượt: không lưu lịch sử, không streaming, không system prompt, chưa gắn với user. `ChatResponse.timestamp`/`user_id` đang là giá trị giả.
- DB dev: `admin` (ADMIN) và 2 user test `test_9177`, `vn_7968` (USER).

## Việc còn tồn / vấn đề đã biết

- Refresh token không thu hồi được (không có logout/blacklist); cần lưu token (DB/Redis) nếu muốn.
- `REFRESH_TOKEN_EXPIRE_DAYS = 3000` (quá dài, nên 7–30).
- Mật khẩu admin dev là mật khẩu yếu.
- Chưa cấu hình CORS (frontend khác origin sẽ bị chặn).
- `/chat-bot/send` chưa yêu cầu đăng nhập, trả `str(e)` cho client và debug bằng `print`.
- `core/config.py` có import thừa `from xml.parsers.expat import model`; `.env.example` khai báo `DATABASE_URL` hai lần.
- `backend/.DS_Store` bị commit.
