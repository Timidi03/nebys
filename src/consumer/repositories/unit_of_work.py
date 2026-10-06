from sqlalchemy.ext.asyncio import AsyncSession

from src.common.database import UnitOfWork
from src.consumer.repositories.payment import PaymentRepository


class PaymentUnitOfWork(UnitOfWork):
    payments: PaymentRepository

    def _init_repositories(self, session: AsyncSession) -> None:
        self.payments = PaymentRepository(session)
