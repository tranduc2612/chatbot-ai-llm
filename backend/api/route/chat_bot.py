from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from schemas.chat_bot import ChatResponse
from services.llm_service import llm_service
from core.config import settings

router = APIRouter(prefix="/chat-bot", tags=["chat-bot"])

@router.get("/send")
async def send_message(message: str = ""):
    try:
        response = await llm_service.generate_response(message)

        print("LLM Response:", response)

        return ChatResponse(
            message=message,
            response=response,
            model=settings.CF_MODEL
            if settings.LLM_PROVIDER == "cloudflare"
            else settings.OLLAMA_MODEL,
            timestamp="huhuu",
            user_id="huhuu"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))