from abc import ABC, abstractmethod

import httpx

from src.common.exceptions import TemporaryError
from src.common.models import Payment


class NotificationError(TemporaryError):
    pass


class Notifier(ABC):
    @abstractmethod
    async def notify(self, payment: Payment) -> None:
        """Сообщить клиенту о результате платежа. При ошибке - NotificationError."""


class WebhookNotifier(Notifier):
    def __init__(self, client: httpx.AsyncClient):
        self.client = client

    async def notify(self, payment: Payment) -> None:
        data = {
            "payment_id": str(payment.id),
            "status": payment.status.value,
            "amount": str(payment.amount),
            "currency": payment.currency.value,
            "metadata": payment.meta,
            "processed_at": payment.processed_at.isoformat(),
        }
        try:
            resp = await self.client.post(
                payment.webhook_url, json=data, headers={"X-Webhook-Id": data["payment_id"]}
            )
        except httpx.HTTPError as e:
            raise NotificationError(repr(e)) from e
        if not resp.is_success:
            raise NotificationError(f"webhook responded with {resp.status_code}")
