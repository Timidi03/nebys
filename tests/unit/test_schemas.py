import pytest
from pydantic import ValidationError

from src.api.schemas import PaymentCreate


def make(**kwargs):
    data = {"amount": "100", "currency": "RUB", "webhook_url": "https://example.com/hook"}
    data.update(kwargs)
    return PaymentCreate(**data)


@pytest.mark.parametrize("amount", ["100", "100.0", "100.00", 100, 100.0])
def test_same_amount_same_hash(amount):
    assert make(amount=amount).get_hash() == make(amount="100.00").get_hash()


def test_metadata_order_does_not_change_hash():
    assert make(metadata={"a": 1, "b": 2}).get_hash() == make(metadata={"b": 2, "a": 1}).get_hash()


def test_different_body_different_hash():
    assert make(amount="100.01").get_hash() != make().get_hash()
    assert make(currency="USD").get_hash() != make().get_hash()


@pytest.mark.parametrize(
    "kwargs",
    [
        {"amount": "0"},
        {"amount": "-1"},
        {"amount": "1.001"},
        {"currency": "BTC"},
        {"webhook_url": "not-a-url"},
    ],
)
def test_validation(kwargs):
    with pytest.raises(ValidationError):
        make(**kwargs)
