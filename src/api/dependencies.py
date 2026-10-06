import secrets

from fastapi import Depends, HTTPException, Request, Security
from fastapi.security import APIKeyHeader

from src.api.repositories.unit_of_work import PaymentUnitOfWork
from src.api.services.payment_service import PaymentService

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def get_uow(request: Request) -> PaymentUnitOfWork:
    return PaymentUnitOfWork(request.app.state.session_factory)


def get_payment_service(uow: PaymentUnitOfWork = Depends(get_uow)) -> PaymentService:
    return PaymentService(uow)


async def check_api_key(request: Request, api_key: str | None = Security(api_key_header)):
    expected = request.app.state.settings.api_key
    if not api_key or not secrets.compare_digest(api_key.encode(), expected.encode()):
        raise HTTPException(status_code=401, detail="Invalid API key")
