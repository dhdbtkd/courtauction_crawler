from fastapi import APIRouter
from .dashboard import router as dashboard_router

router = APIRouter(prefix="/admin", tags=["Admin"])

router.include_router(dashboard_router)
