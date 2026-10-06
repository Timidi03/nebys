import uuid
from datetime import UTC, datetime

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import Payment, PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_for_update(self, payment_id: uuid.UUID) -> Payment | None:
        return await self.session.scalar(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )

    async def finish(self, payment_id: uuid.UUID, status: PaymentStatus) -> Payment:
        return await self.session.scalar(
            update(Payment)
            .where(Payment.id == payment_id)
            .values(status=status, processed_at=datetime.now(UTC))
            .returning(Payment)
            .execution_options(populate_existing=True)
        )

    async def mark_notified(self, payment_id: uuid.UUID) -> None:
        await self.session.execute(
            update(Payment).where(Payment.id == payment_id).values(notified_at=func.now())
        )
