import asyncio

import pytest

from src.common.models import PaymentStatus
from src.consumer.clients.gateway import GatewayError
from src.consumer.clients.notifier import NotificationError
from src.consumer.repositories.unit_of_work import PaymentUnitOfWork
from src.consumer.services.processor import PaymentProcessor
from tests.utils import FakeGateway, FakeNotifier


def make_processor(session_factory, gateway, *notifiers, gateway_timeout=10.0):
    return PaymentProcessor(
        lambda: PaymentUnitOfWork(session_factory), gateway, list(notifiers), gateway_timeout
    )


async def test_process_payment(session_factory, new_payment, get_payment):
    payment = await new_payment()
    notifier = FakeNotifier()

    await make_processor(session_factory, FakeGateway(success=False), notifier).process(payment.id)

    payment = await get_payment(payment.id)
    assert payment.status == PaymentStatus.failed
    assert payment.processed_at is not None
    assert payment.notified_at is not None
    assert notifier.sent[0].status == PaymentStatus.failed


async def test_duplicate_message_is_ignored(session_factory, new_payment):
    payment = await new_payment()
    gateway, notifier = FakeGateway(), FakeNotifier()
    processor = make_processor(session_factory, gateway, notifier)

    await processor.process(payment.id)
    await processor.process(payment.id)

    assert gateway.calls == 1
    assert len(notifier.sent) == 1


async def test_notification_retry_does_not_charge_again(session_factory, new_payment, get_payment):
    payment = await new_payment()
    gateway, notifier = FakeGateway(), FakeNotifier(fail=True)
    processor = make_processor(session_factory, gateway, notifier)

    with pytest.raises(NotificationError):
        await processor.process(payment.id)
    assert (await get_payment(payment.id)).status == PaymentStatus.succeeded

    notifier.fail = False
    await processor.process(payment.id)

    assert gateway.calls == 1
    assert (await get_payment(payment.id)).notified_at is not None


async def test_all_notifiers_are_called(session_factory, new_payment):
    payment = await new_payment()
    webhook, email = FakeNotifier(), FakeNotifier()

    await make_processor(session_factory, FakeGateway(), webhook, email).process(payment.id)

    assert len(webhook.sent) == len(email.sent) == 1


async def test_parallel_processing_charges_once(session_factory, new_payment, get_payment):
    payment = await new_payment()
    gateway = FakeGateway(delay=0.3)
    first = make_processor(session_factory, gateway, FakeNotifier())
    second = make_processor(session_factory, gateway, FakeNotifier())

    await asyncio.gather(first.process(payment.id), second.process(payment.id))

    assert gateway.calls == 1
    assert (await get_payment(payment.id)).status == PaymentStatus.succeeded


async def test_gateway_timeout_releases_payment_for_retry(
    session_factory, new_payment, get_payment
):
    payment = await new_payment()
    slow = make_processor(session_factory, FakeGateway(delay=5), gateway_timeout=0.2)

    with pytest.raises(GatewayError):
        await slow.process(payment.id)
    assert (await get_payment(payment.id)).status == PaymentStatus.pending

    # блокировка строки снята, повторная попытка проходит
    await make_processor(session_factory, FakeGateway(), FakeNotifier()).process(payment.id)
    assert (await get_payment(payment.id)).status == PaymentStatus.succeeded
