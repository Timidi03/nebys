from collections.abc import Sequence
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.models import OutboxMessage


class OutboxRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    def add(self, event_type: str, payload: dict) -> None:
        self.session.add(OutboxMessage(event_type=event_type, payload=payload))

    async def get_unpublished(self, limit: int) -> Sequence[OutboxMessage]:
        stmt = (
            select(OutboxMessage)
            .where(OutboxMessage.published_at.is_(None))
            .order_by(OutboxMessage.created_at)
            .limit(limit)
            .with_for_update(skip_locked=True)
        )  # чтобы несколько relay не брали одни и те же записи
        return (await self.session.scalars(stmt)).all()

    def mark_published(self, message: OutboxMessage) -> None:
        message.published_at = datetime.now(UTC)
