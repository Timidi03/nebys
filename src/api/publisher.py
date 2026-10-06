from faststream.rabbit import RabbitBroker

from src.common.broker import EVENT_ROUTES, payments_exchange


class EventPublisher:
    def __init__(self, broker: RabbitBroker):
        self.broker = broker

    async def publish(self, event_type: str, payload: dict, message_id: str) -> None:
        await self.broker.publish(
            payload,
            exchange=payments_exchange,
            routing_key=EVENT_ROUTES[event_type],
            message_id=message_id,
            message_type=event_type,
            persist=True,
            timeout=10,
        )
