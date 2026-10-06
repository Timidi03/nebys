from fastapi import APIRouter, Depends

from src.api.dependencies import check_api_key
from src.api.routes.v1 import payments

router = APIRouter(prefix="/v1", dependencies=[Depends(check_api_key)])
router.include_router(payments.router)
