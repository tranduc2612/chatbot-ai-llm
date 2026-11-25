from fastapi import APIRouter

from api.route import chat_bot


api_router = APIRouter()
api_router.include_router(chat_bot.router)
# api_router.include_router(auth.router)