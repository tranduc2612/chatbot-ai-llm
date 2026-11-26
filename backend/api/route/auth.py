from fastapi import APIRouter, HTTPException

from schemas.auth import Token


router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login", response_model=Token)
async def login():
    # Implement your login logic here
    # For demonstration purposes, we'll return a dummy token
    

    return Token(access_token="dummy_access_token")