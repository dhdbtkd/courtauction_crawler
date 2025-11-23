# routers/__init__.py

from fastapi import APIRouter

# 공용 라우터 생성 (원하면 생략 가능)
router = APIRouter()

# 서브 라우터 import
from .admin import router as admin_router

# 묶어서 export
router.include_router(admin_router)

__all__ = ["router"]
