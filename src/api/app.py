import asyncio
import contextlib
from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.api import routes
from src.api.publisher import EventPublisher
from src.api.repositories.unit_of_work import PaymentUnitOfWork
from src.api.services.outbox_relay import OutboxRelay
from src.common.broker import create_broker, setup_topology
from src.common.config import Settings, get_settings
from src.common.database import create_engine, create_session_factory
from src.common.logger import logger


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = create_engine(settings.database_url)
        session_factory = create_session_factory(engine)
        app.state.session_factory = session_factory

        broker = create_broker(settings)
        relay_task = None
        if settings.outbox_relay_enabled:
            relay = OutboxRelay(
                lambda: PaymentUnitOfWork(session_factory),
                EventPublisher(broker),
                settings.outbox_batch_size,
            )
            relay_task = asyncio.create_task(run_outbox_relay(relay, broker, settings))

        yield

        if relay_task:
            relay_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await relay_task
        await broker.stop()
        await engine.dispose()

    app = FastAPI(title="Payments service", lifespan=lifespan)
    app.state.settings = settings
    app.include_router(routes.router)
    return app


async def run_outbox_relay(relay: OutboxRelay, broker, settings: Settings) -> None:
    while True:
        try:
            await broker.connect()
            await setup_topology(broker, settings)
            break
        except Exception as e:
            logger.warning("rabbitmq is unavailable (%s), retry in 5s", e)
            await asyncio.sleep(5)

    logger.info("outbox relay started")
    await relay.run(settings.outbox_poll_interval)
