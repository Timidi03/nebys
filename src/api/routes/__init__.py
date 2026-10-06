from fastapi import APIRouter

from src.api.routes import v1

router = APIRouter(prefix="/api")
router.include_router(v1.router)
