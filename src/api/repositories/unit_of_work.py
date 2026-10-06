from sqlalchemy.ext.asyncio import AsyncSession

from src.api.repositories.outbox import OutboxRepository
from src.api.repositories.payment import PaymentRepository
from src.common.database import UnitOfWork


class PaymentUnitOfWork(UnitOfWork):
    payments: PaymentRepository
    outbox: OutboxRepository

    def _init_repositories(self, session: AsyncSession) -> None:
        self.payments = PaymentRepository(session)
        self.outbox = OutboxRepository(session)
