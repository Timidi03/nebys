import json

from src.common.broker import dead_letter_queue, payments_exchange
from tests.utils import wait_for


async def get_from_dlq(broker):
    dlq = await broker.declare_queue(dead_letter_queue)
    messages = []

    async def check():
        msg = await dlq.get(fail=False)
        if msg:
            messages.append(msg)
        return bool(messages)

    await wait_for(check)
    return messages[0]


async def publish_created(broker, payment_id):
    await broker.publish(
        {"payment_id": str(payment_id)}, exchange=payments_exchange, routing_key="payments.new"
    )


async def test_message_is_processed(consumer, broker, new_payment, get_payment, notifier):
    payment = await new_payment()
    await publish_created(broker, payment.id)

    async def notified():
        return (await get_payment(payment.id)).notified_at is not None

    await wait_for(notified)
    assert len(notifier.sent) == 1


async def test_failed_notification_goes_to_dlq_after_retries(
    consumer, broker, new_payment, gateway, notifier, settings
):
    notifier.fail = True
    payment = await new_payment()
    await publish_created(broker, payment.id)

    msg = await get_from_dlq(broker)

    assert json.loads(msg.body) == {"payment_id": str(payment.id)}
    assert msg.headers["x-retry"] == settings.max_attempts - 1
    assert len(notifier.sent) == settings.max_attempts
    assert gateway.calls == 1


async def test_bad_message_goes_to_dlq(consumer, broker, gateway):
    await broker.publish({"foo": "bar"}, exchange=payments_exchange, routing_key="payments.new")

    msg = await get_from_dlq(broker)

    assert json.loads(msg.body) == {"foo": "bar"}
    assert "x-retry" not in msg.headers
    assert gateway.calls == 0
