import asyncio
from contextlib import asynccontextmanager

import httpx

from src.api.app import create_app
from src.consumer.clients.gateway import PaymentGateway
from src.consumer.clients.notifier import NotificationError, Notifier


class FakeGateway(PaymentGateway):
    def __init__(self, success=True, delay=0):
        self.success = success
        self.delay = delay
        self.calls = 0

    async def charge(self, payment):
        self.calls += 1
        await asyncio.sleep(self.delay)
        return self.success


class FakeNotifier(Notifier):
    def __init__(self, fail=False):
        self.fail = fail
        self.sent = []

    async def notify(self, payment):
        self.sent.append(payment)
        if self.fail:
            raise NotificationError("webhook responded with 500")


async def wait_for(check, timeout=10):
    async with asyncio.timeout(timeout):
        while not await check():
            await asyncio.sleep(0.05)


@asynccontextmanager
async def api_client(settings):
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app),
            base_url="http://test",
            headers={"X-API-Key": settings.api_key},
        ) as client:
            yield client
