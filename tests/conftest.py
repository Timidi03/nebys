import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text
from testcontainers.postgres import PostgresContainer
from testcontainers.rabbitmq import RabbitMqContainer

from src.api.repositories.unit_of_work import PaymentUnitOfWork
from src.api.schemas import PaymentCreate
from src.api.services.payment_service import PaymentService
from src.common.broker import (
    create_broker,
    dead_letter_queue,
    payments_queue,
    retry_delays,
    retry_queue,
    setup_topology,
)
from src.common.config import Settings
from src.common.database import create_engine, create_session_factory
from src.common.models import Payment
from src.consumer.app import create_consumer
from tests.utils import FakeGateway, FakeNotifier

API_KEY = "test-key"


@pytest.fixture(scope="session")
def postgres_url():
    with PostgresContainer("postgres:17-alpine", driver="asyncpg") as pg:
        url = pg.get_connection_url()
        os.environ["DATABASE_URL"] = url
        command.upgrade(Config("alembic.ini"), "head")
        yield url


@pytest.fixture(scope="session")
def rabbitmq_url():
    with RabbitMqContainer("rabbitmq:4.1-alpine") as rabbit:
        host = rabbit.get_container_host_ip()
        port = rabbit.get_exposed_port(5672)
        yield f"amqp://guest:guest@{host}:{port}/"


@pytest.fixture(scope="session")
def settings(postgres_url, rabbitmq_url):
    return Settings(
        api_key=API_KEY,
        database_url=postgres_url,
        rabbitmq_url=rabbitmq_url,
        retry_base_delay=0.1,
        outbox_poll_interval=0.1,
    )


@pytest.fixture(scope="session")
async def session_factory(settings):
    engine = create_engine(settings.database_url)
    yield create_session_factory(engine)
    await engine.dispose()


@pytest.fixture
async def clean_db(session_factory):
    async with session_factory() as session:
        await session.execute(text("TRUNCATE payments, outbox"))
        await session.commit()


@pytest.fixture
async def broker(settings):
    broker = create_broker(settings)
    async with broker:
        await setup_topology(broker, settings)
        queues = [payments_queue, dead_letter_queue]
        queues += [retry_queue(d) for d in retry_delays(settings)]
        for q in queues:
            await (await broker.declare_queue(q)).purge()
        yield broker


@pytest.fixture
def new_payment(session_factory):
    async def create(key="key-1", **kwargs):
        data = {"amount": "100", "currency": "RUB", "webhook_url": "https://example.com/hook"}
        data.update(kwargs)
        service = PaymentService(PaymentUnitOfWork(session_factory))
        return await service.create(PaymentCreate(**data), key)

    return create


@pytest.fixture
def get_payment(session_factory):
    async def get(payment_id):
        async with session_factory() as session:
            return await session.get(Payment, payment_id)

    return get


@pytest.fixture
def gateway():
    return FakeGateway()


@pytest.fixture
def notifier():
    return FakeNotifier()


@pytest.fixture
async def consumer(broker, settings, gateway, notifier):
    app = create_consumer(settings, gateway=gateway, notifiers=[notifier])
    await app.start()
    yield app
    await app.stop()
