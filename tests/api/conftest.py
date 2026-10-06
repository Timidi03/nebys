import pytest

from tests.utils import api_client


@pytest.fixture(autouse=True)
async def _clean(clean_db):
    pass


@pytest.fixture
async def client(settings):
    async with api_client(settings.model_copy(update={"outbox_relay_enabled": False})) as c:
        yield c
