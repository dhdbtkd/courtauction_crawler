from fastapi import Header, HTTPException
from config.settings import settings


async def get_current_user(token: str = Header(None)):
    if token is None:
        raise HTTPException(401, "Token required")
    return token


async def verify_admin(x_api_key: str = Header(None)):
    print("🔐 x-api-key received:", x_api_key)
    if x_api_key != settings.ADMIN_SECRET:
        raise HTTPException(403, "Forbidden")
    return True
