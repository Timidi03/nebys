import asyncio
from collections.abc import Callable

from src.api.publisher import EventPublisher
from src.api.repositories.unit_of_work import PaymentUnitOfWork
from src.common.logger import logger


class OutboxRelay:
    def __init__(
        self,
        uow_factory: Callable[[], PaymentUnitOfWork],
        publisher: EventPublisher,
        batch_size: int = 100,
    ):
        self.uow_factory = uow_factory
        self.publisher = publisher
        self.batch_size = batch_size

    async def publish_batch(self) -> int:
        published = 0
        async with self.uow_factory() as uow:
            try:
                for msg in await uow.outbox.get_unpublished(self.batch_size):
                    await self.publisher.publish(msg.event_type, msg.payload, str(msg.id))
                    uow.outbox.mark_published(msg)
                    published += 1
            finally:
                await uow.commit()
        return published

    async def run(self, poll_interval: float, max_backoff: float = 30.0) -> None:
        backoff = poll_interval
        while True:
            try:
                published = await self.publish_batch()
            except Exception as e:
                logger.warning("outbox relay failed: %r, retry in %.1fs", e, backoff)
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                continue

            backoff = poll_interval
            if published:
                logger.info("published %d messages", published)
            if published < self.batch_size:
                await asyncio.sleep(poll_interval)
