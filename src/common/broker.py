from faststream.rabbit import Channel, ExchangeType, RabbitBroker, RabbitExchange, RabbitQueue

from src.common.config import Settings

PAYMENT_CREATED = "payment.created"

payments_exchange = RabbitExchange("payments", type=ExchangeType.DIRECT, durable=True)
retry_exchange = RabbitExchange("payments.retry", type=ExchangeType.DIRECT, durable=True)
dead_letter_exchange = RabbitExchange("payments.dlx", type=ExchangeType.DIRECT, durable=True)

payments_queue = RabbitQueue(
    "payments.new",
    durable=True,
    arguments={
        "x-dead-letter-exchange": "payments.dlx",
        "x-dead-letter-routing-key": "payments.dlq",
    },
)
dead_letter_queue = RabbitQueue("payments.dlq", durable=True)

EVENT_ROUTES = {
    PAYMENT_CREATED: payments_queue.name,
}


def retry_queue(delay_ms: int) -> RabbitQueue:
    return RabbitQueue(
        f"payments.retry.{delay_ms}ms",
        durable=True,
        arguments={
            "x-message-ttl": delay_ms,
            "x-dead-letter-exchange": "payments",
            "x-dead-letter-routing-key": "payments.new",
        },
    )


def retry_delays(settings: Settings) -> list[int]:
    return [int(settings.retry_base_delay * 1000 * 2**i) for i in range(settings.max_attempts - 1)]


def create_broker(settings: Settings) -> RabbitBroker:
    return RabbitBroker(
        settings.rabbitmq_url,
        default_channel=Channel(prefetch_count=10, on_return_raises=True),
    )


async def setup_topology(broker: RabbitBroker, settings: Settings) -> None:
    exchange = await broker.declare_exchange(payments_exchange)
    retry = await broker.declare_exchange(retry_exchange)
    dlx = await broker.declare_exchange(dead_letter_exchange)

    queue = await broker.declare_queue(payments_queue)
    await queue.bind(exchange, routing_key=payments_queue.name)

    dlq = await broker.declare_queue(dead_letter_queue)
    await dlq.bind(dlx, routing_key=dead_letter_queue.name)

    for delay in retry_delays(settings):
        q = await broker.declare_queue(retry_queue(delay))
        await q.bind(retry, routing_key=q.name)
