import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import Payment


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def get_by_idempotency_key(self, key: str) -> Payment | None:
        return await self.session.scalar(select(Payment).where(Payment.idempotency_key == key))

    async def create_if_not_exists(self, **values) -> Payment | None:
        stmt = (
            insert(Payment)
            .values(**values)
            .on_conflict_do_nothing(index_elements=["idempotency_key"])
            .returning(Payment)
        )
        return await self.session.scalar(stmt)
