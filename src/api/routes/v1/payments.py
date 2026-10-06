import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from src.api.dependencies import get_payment_service
from src.api.schemas import PaymentAccepted, PaymentCreate, PaymentOut
from src.api.services.payment_service import IdempotencyKeyConflict, PaymentService

router = APIRouter(prefix="/payments", tags=["payments"])


@router.post("", status_code=202, response_model=PaymentAccepted)
async def create_payment(
    data: PaymentCreate,
    idempotency_key: Annotated[str, Header(min_length=1, max_length=255)],
    service: PaymentService = Depends(get_payment_service),
):
    try:
        payment = await service.create(data, idempotency_key)
    except IdempotencyKeyConflict:
        raise HTTPException(
            status_code=422, detail="Idempotency-Key already used with a different request"
        ) from None
    return PaymentAccepted(
        payment_id=payment.id, status=payment.status, created_at=payment.created_at
    )


@router.get("/{payment_id}", response_model=PaymentOut)
async def get_payment(
    payment_id: uuid.UUID, service: PaymentService = Depends(get_payment_service)
):
    payment = await service.get(payment_id)
    if payment is None:
        raise HTTPException(status_code=404, detail="Payment not found")
    return payment
