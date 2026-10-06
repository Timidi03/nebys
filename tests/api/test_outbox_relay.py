import asyncio
import json

import pytest
from sqlalchemy import select

from src.api.publisher import EventPublisher
from src.api.repositories.unit_of_work import PaymentUnitOfWork
from src.api.services.outbox_relay import OutboxRelay
from src.common.broker import payments_queue
from src.common.models import OutboxMessage


class BrokenPublisher:
    async def publish(self, event_type, payload, message_id):
        raise ConnectionError("rabbit is down")


class SlowPublisher:
    def __init__(self):
        self.published = []

    async def publish(self, event_type, payload, message_id):
        await asyncio.sleep(0.01)
        self.published.append(message_id)


def make_relay(session_factory, publisher, batch_size=100):
    return OutboxRelay(lambda: PaymentUnitOfWork(session_factory), publisher, batch_size)


async def get_outbox(session_factory):
    async with session_factory() as session:
        return (await session.scalars(select(OutboxMessage))).all()


async def test_relay_publishes_to_rabbit(broker, session_factory, new_payment):
    payment = await new_payment()
    relay = make_relay(session_factory, EventPublisher(broker))

    assert await relay.publish_batch() == 1
    assert await relay.publish_batch() == 0

    queue = await broker.declare_queue(payments_queue)
    msg = await queue.get(fail=False)
    assert json.loads(msg.body) == {"payment_id": str(payment.id)}
    assert (await get_outbox(session_factory))[0].published_at is not None


async def test_relay_keeps_message_if_broker_is_down(session_factory, new_payment):
    await new_payment()

    with pytest.raises(ConnectionError):
        await make_relay(session_factory, BrokenPublisher()).publish_batch()
    assert (await get_outbox(session_factory))[0].published_at is None


async def test_parallel_relays_do_not_publish_twice(session_factory, new_payment):
    for i in range(30):
        await new_payment(key=f"key-{i}")
    publisher = SlowPublisher()
    relays = [make_relay(session_factory, publisher, batch_size=5) for _ in range(3)]

    async def run(relay):
        while await relay.publish_batch():
            pass

    await asyncio.gather(*[run(r) for r in relays])

    assert len(publisher.published) == 30
    assert len(set(publisher.published)) == 30
