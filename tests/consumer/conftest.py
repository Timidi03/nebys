import pytest


@pytest.fixture(autouse=True)
async def _clean(clean_db):
    pass
