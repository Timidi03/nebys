import uuid

from src.api.repositories.unit_of_work import PaymentUnitOfWork
from src.api.schemas import PaymentCreate
from src.common.broker import PAYMENT_CREATED
from src.common.models import Payment


class IdempotencyKeyConflict(Exception):
    pass


class PaymentService:
    def __init__(self, uow: PaymentUnitOfWork):
        self.uow = uow

    async def create(self, data: PaymentCreate, idempotency_key: str) -> Payment:
        request_hash = data.get_hash()

        async with self.uow:
            payment = await self.uow.payments.create_if_not_exists(
                amount=data.amount,
                currency=data.currency,
                description=data.description,
                meta=data.metadata,
                webhook_url=str(data.webhook_url),
                idempotency_key=idempotency_key,
                request_hash=request_hash,
            )

            if payment is None:
                # повторный запрос с тем же ключом
                payment = await self.uow.payments.get_by_idempotency_key(idempotency_key)
                if payment.request_hash != request_hash:
                    raise IdempotencyKeyConflict()
                return payment

            self.uow.outbox.add(PAYMENT_CREATED, {"payment_id": str(payment.id)})
            await self.uow.commit()
            return payment

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        async with self.uow:
            return await self.uow.payments.get(payment_id)
