from contextlib import asynccontextmanager
from typing import AsyncGenerator, Callable, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import db_manager


class UnitOfWork:
    """
    Minimal async Unit of Work helper to centralize session lifecycle.
    Services can depend on this to ensure commit/rollback happens in one place.
    """

    def __init__(self, session_factory: Optional[Callable[[], AsyncSession]] = None):
        self._session_factory = session_factory or db_manager.async_session_maker

    @asynccontextmanager
    async def __call__(self) -> AsyncGenerator[AsyncSession, None]:
        async with self._session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
