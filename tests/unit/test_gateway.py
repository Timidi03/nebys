import uuid

from src.common.models import Payment
from src.consumer.clients.gateway import EmulatedGateway


async def test_same_payment_is_not_charged_twice():
    gateway = EmulatedGateway(min_delay=0, max_delay=0, success_rate=0.5)
    payments = [Payment(id=uuid.uuid4()) for _ in range(20)]

    first = [await gateway.charge(p) for p in payments]
    second = [await gateway.charge(p) for p in payments]

    assert first == second
