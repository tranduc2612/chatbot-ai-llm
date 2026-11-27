from fastapi import APIRouter

from api.route import chat_bot
from api.route import auth
from api.route import user


api_router = APIRouter()
api_router.include_router(chat_bot.router)
api_router.include_router(auth.router)
api_router.include_router(user.router)
