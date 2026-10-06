import uuid

from faststream import AckPolicy
from faststream.exceptions import RejectMessage
from faststream.rabbit import RabbitBroker, RabbitMessage

from src.common.broker import (
    payments_exchange,
    payments_queue,
    retry_delays,
    retry_exchange,
    retry_queue,
)
from src.common.config import Settings
from src.common.exceptions import TemporaryError
from src.common.logger import logger
from src.consumer.services.processor import PaymentNotFound, PaymentProcessor


def register_handlers(broker: RabbitBroker, processor: PaymentProcessor, settings: Settings):
    delays = retry_delays(settings)

    @broker.subscriber(payments_queue, payments_exchange, ack_policy=AckPolicy.REJECT_ON_ERROR)
    async def handle_payment_created(body: dict, message: RabbitMessage):
        payment_id = uuid.UUID(body["payment_id"])
        retry = int(message.headers.get("x-retry", 0))

        try:
            await processor.process(payment_id)
        except PaymentNotFound:
            logger.error("payment %s not found", payment_id)
            raise RejectMessage() from None
        except TemporaryError as e:
            if retry >= len(delays):
                logger.error("payment %s: retries exhausted, sending to DLQ", payment_id)
                raise RejectMessage() from e

            delay = delays[retry]
            logger.warning("payment %s: %s, retry #%d in %dms", payment_id, e, retry + 1, delay)
            await broker.publish(
                body,
                exchange=retry_exchange,
                routing_key=retry_queue(delay).name,
                headers={"x-retry": retry + 1},
                persist=True,
            )
