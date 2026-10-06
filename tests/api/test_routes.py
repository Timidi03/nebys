import asyncio
import uuid

from sqlalchemy import func, select

from src.common.models import OutboxMessage, Payment

BODY = {
    "amount": "1234.56",
    "currency": "RUB",
    "description": "order 1",
    "metadata": {"order_id": 1},
    "webhook_url": "https://example.com/hook",
}


async def count(session_factory, model):
    async with session_factory() as session:
        return await session.scalar(select(func.count()).select_from(model))


async def test_create_payment(client, session_factory):
    resp = await client.post("/api/v1/payments", json=BODY, headers={"Idempotency-Key": "k1"})
    assert resp.status_code == 202
    assert resp.json()["status"] == "pending"
    payment_id = resp.json()["payment_id"]

    async with session_factory() as session:
        outbox = (await session.scalars(select(OutboxMessage))).all()
    assert len(outbox) == 1
    assert outbox[0].payload == {"payment_id": payment_id}
    assert outbox[0].published_at is None

    resp = await client.get(f"/api/v1/payments/{payment_id}")
    assert resp.status_code == 200
    assert resp.json()["amount"] == "1234.56"
    assert resp.json()["metadata"] == {"order_id": 1}


async def test_same_idempotency_key_returns_same_payment(client, session_factory):
    r1 = await client.post("/api/v1/payments", json=BODY, headers={"Idempotency-Key": "k1"})
    r2 = await client.post(
        "/api/v1/payments", json={**BODY, "amount": 1234.560}, headers={"Idempotency-Key": "k1"}
    )

    assert r2.status_code == 202
    assert r1.json() == r2.json()
    assert await count(session_factory, Payment) == 1
    assert await count(session_factory, OutboxMessage) == 1


async def test_same_key_different_body(client):
    await client.post("/api/v1/payments", json=BODY, headers={"Idempotency-Key": "k1"})
    resp = await client.post(
        "/api/v1/payments", json={**BODY, "amount": "1"}, headers={"Idempotency-Key": "k1"}
    )
    assert resp.status_code == 422


async def test_parallel_requests_with_same_key(client, session_factory):
    responses = await asyncio.gather(
        *[
            client.post("/api/v1/payments", json=BODY, headers={"Idempotency-Key": "k1"})
            for _ in range(20)
        ]
    )
    assert all(r.status_code == 202 for r in responses)
    assert len({r.json()["payment_id"] for r in responses}) == 1
    assert await count(session_factory, Payment) == 1
    assert await count(session_factory, OutboxMessage) == 1


async def test_auth(client):
    resp = await client.get(f"/api/v1/payments/{uuid.uuid4()}", headers={"X-API-Key": "wrong"})
    assert resp.status_code == 401

    resp = await client.get(f"/api/v1/payments/{uuid.uuid4()}")
    assert resp.status_code == 404


async def test_idempotency_key_required(client):
    resp = await client.post("/api/v1/payments", json=BODY)
    assert resp.status_code == 422
