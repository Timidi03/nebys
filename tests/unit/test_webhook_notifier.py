import uuid
from datetime import UTC, datetime
from decimal import Decimal

import httpx
import pytest

from src.common.models import Currency, Payment, PaymentStatus
from src.consumer.clients.notifier import NotificationError, WebhookNotifier

PAYMENT = Payment(
    id=uuid.uuid4(),
    amount=Decimal("10.00"),
    currency=Currency.RUB,
    meta={"order_id": 1},
    status=PaymentStatus.succeeded,
    webhook_url="https://example.com/hook",
    processed_at=datetime.now(UTC),
)


def notifier_with(handler):
    return WebhookNotifier(httpx.AsyncClient(transport=httpx.MockTransport(handler)))


async def test_sends_webhook():
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(200)

    await notifier_with(handler).notify(PAYMENT)

    assert str(requests[0].url) == "https://example.com/hook"
    assert requests[0].headers["X-Webhook-Id"] == str(PAYMENT.id)
    assert b'"status":"succeeded"' in requests[0].content


async def test_error_status_raises():
    with pytest.raises(NotificationError):
        await notifier_with(lambda r: httpx.Response(500)).notify(PAYMENT)


async def test_connection_error_raises():
    def handler(request):
        raise httpx.ConnectError("refused")

    with pytest.raises(NotificationError):
        await notifier_with(handler).notify(PAYMENT)
