from sqlalchemy.exc import InterfaceError, OperationalError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.common.exceptions import DatabaseUnavailable


class Base(DeclarativeBase):
    pass


def create_engine(database_url: str) -> AsyncEngine:
    return create_async_engine(database_url, pool_pre_ping=True)


def create_session_factory(engine: AsyncEngine) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


class UnitOfWork:
    """Одна транзакция. Наследники создают в _init_repositories нужные репозитории."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self.session_factory = session_factory

    def _init_repositories(self, session: AsyncSession) -> None:
        pass

    async def __aenter__(self):
        self.session = self.session_factory()
        try:
            await self.session.connection()
        except (OperationalError, InterfaceError, OSError) as e:
            await self.session.close()
            raise DatabaseUnavailable(str(e)) from e
        self._init_repositories(self.session)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if exc is not None:
            await self.session.rollback()
        await self.session.close()
        if isinstance(exc, (OperationalError, InterfaceError)):
            raise DatabaseUnavailable(str(exc)) from exc

    async def commit(self) -> None:
        await self.session.commit()
