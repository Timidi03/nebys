from src.common.models import PaymentStatus
from tests.utils import api_client, wait_for


async def test_payment_flow(clean_db, consumer, settings, notifier):
    async with api_client(settings) as client:
        resp = await client.post(
            "/api/v1/payments",
            json={"amount": "100", "currency": "RUB", "webhook_url": "https://example.com/hook"},
            headers={"Idempotency-Key": "e2e"},
        )
        assert resp.status_code == 202
        payment_id = resp.json()["payment_id"]

        async def notified():
            resp = await client.get(f"/api/v1/payments/{payment_id}")
            return resp.json()["notified_at"] is not None

        await wait_for(notified)

        payment = (await client.get(f"/api/v1/payments/{payment_id}")).json()
        assert payment["status"] == PaymentStatus.succeeded
        assert [str(p.id) for p in notifier.sent] == [payment_id]
