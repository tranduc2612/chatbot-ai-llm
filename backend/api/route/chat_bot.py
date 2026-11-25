from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/chat-bot", tags=["chat-bot"])

@router.get("/send")
async def get_me():
    
    return "send message"