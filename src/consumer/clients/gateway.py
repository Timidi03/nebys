import asyncio
import random
import uuid
from abc import ABC, abstractmethod

from src.common.exceptions import TemporaryError
from src.common.models import Payment


class GatewayError(TemporaryError):
    pass


class PaymentGateway(ABC):
    @abstractmethod
    async def charge(self, payment: Payment) -> bool:
        """True - платеж прошел, False - отклонен.

        payment.id передается шлюзу как ключ идемпотентности: повторный вызов для того же
        платежа не списывает деньги второй раз, а возвращает прежний результат.
        """


class EmulatedGateway(PaymentGateway):
    def __init__(self, min_delay: float = 2, max_delay: float = 5, success_rate: float = 0.9):
        self.min_delay = min_delay
        self.max_delay = max_delay
        self.success_rate = success_rate
        self._results: dict[uuid.UUID, bool] = {}

    async def charge(self, payment: Payment) -> bool:
        if payment.id in self._results:
            return self._results[payment.id]

        await asyncio.sleep(random.uniform(self.min_delay, self.max_delay))
        result = random.random() < self.success_rate
        self._results[payment.id] = result
        return result
