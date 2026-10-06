import asyncio
import uuid
from collections.abc import Callable

from src.common.logger import logger
from src.common.models import Payment, PaymentStatus
from src.consumer.clients.gateway import GatewayError, PaymentGateway
from src.consumer.clients.notifier import Notifier
from src.consumer.repositories.unit_of_work import PaymentUnitOfWork


class PaymentNotFound(Exception):
    pass


class PaymentProcessor:
    def __init__(
        self,
        uow_factory: Callable[[], PaymentUnitOfWork],
        gateway: PaymentGateway,
        notifiers: list[Notifier],
        gateway_timeout: float = 10.0,
    ):
        self.uow_factory = uow_factory
        self.gateway = gateway
        self.notifiers = notifiers
        self.gateway_timeout = gateway_timeout

    async def process(self, payment_id: uuid.UUID) -> None:
        payment = await self._charge(payment_id)
        if payment.notified_at is None:
            await self._notify(payment)

    async def _charge(self, payment_id: uuid.UUID) -> Payment:
        async with self.uow_factory() as uow:
            payment = await uow.payments.get_for_update(payment_id)
            if payment is None:
                raise PaymentNotFound(payment_id)
            if payment.status != PaymentStatus.pending:
                return payment

            # пока ждем шлюз, строка платежа заблокирована - ждать бесконечно нельзя.
            # повторить безопасно: шлюз не спишет второй раз по ключу идемпотентности
            try:
                async with asyncio.timeout(self.gateway_timeout):
                    success = await self.gateway.charge(payment)
            except TimeoutError:
                raise GatewayError(f"gateway timeout ({self.gateway_timeout}s)") from None
            status = PaymentStatus.succeeded if success else PaymentStatus.failed
            payment = await uow.payments.finish(payment_id, status)
            await uow.commit()

        logger.info("payment %s -> %s", payment.id, payment.status.value)
        return payment

    async def _notify(self, payment: Payment) -> None:
        for notifier in self.notifiers:
            await notifier.notify(payment)

        async with self.uow_factory() as uow:
            await uow.payments.mark_notified(payment.id)
            await uow.commit()
