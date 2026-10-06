import httpx
from faststream import FastStream

from src.common.broker import create_broker, setup_topology
from src.common.config import Settings, get_settings
from src.common.database import create_engine, create_session_factory
from src.consumer.clients.gateway import EmulatedGateway, PaymentGateway
from src.consumer.clients.notifier import Notifier, WebhookNotifier
from src.consumer.handlers import register_handlers
from src.consumer.repositories.unit_of_work import PaymentUnitOfWork
from src.consumer.services.processor import PaymentProcessor


def create_consumer(
    settings: Settings | None = None,
    gateway: PaymentGateway | None = None,
    notifiers: list[Notifier] | None = None,
) -> FastStream:
    settings = settings or get_settings()

    engine = create_engine(settings.database_url)
    session_factory = create_session_factory(engine)
    http_client = httpx.AsyncClient(timeout=settings.webhook_timeout)

    gateway = gateway or EmulatedGateway(
        settings.gateway_min_delay, settings.gateway_max_delay, settings.gateway_success_rate
    )
    notifiers = notifiers or [WebhookNotifier(http_client)]
    processor = PaymentProcessor(
        lambda: PaymentUnitOfWork(session_factory),
        gateway,
        notifiers,
        settings.gateway_timeout,
    )

    broker = create_broker(settings)
    register_handlers(broker, processor, settings)
    app = FastStream(broker)

    @app.after_startup
    async def declare_queues():
        await setup_topology(broker, settings)

    @app.after_shutdown
    async def close_resources():
        await http_client.aclose()
        await engine.dispose()

    return app
