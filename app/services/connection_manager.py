from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import sessionmaker
from app.database.schema import Company
from app.utils.encryption import decrypt_string
from typing import Dict
from contextlib import asynccontextmanager

class ExternalConnectionManager:
    def __init__(self):
        self._engines: Dict[int, any] = {}
        self._session_makers: Dict[int, sessionmaker] = {}

    def get_engine(self, company: Company):
        company_id = company.id
        if company_id in self._engines:
            return self._engines[company_id]

        if not company.encrypted_db_connection_string:
            return None

        db_url = decrypt_string(company.encrypted_db_connection_string)
        if not db_url:
            return None

        engine = create_async_engine(db_url, echo=False)
        self._engines[company_id] = engine
        return engine

    def get_session_maker(self, company: Company) -> async_sessionmaker[AsyncSession]:
        company_id = company.id
        if company_id in self._session_makers:
            return self._session_makers[company_id]

        engine = self.get_engine(company)
        if not engine:
            return None
        
        session_maker = async_sessionmaker(engine, expire_on_commit=False)
        self._session_makers[company_id] = session_maker
        return session_maker

    @asynccontextmanager
    async def get_session(self, company: Company):
        session_maker = self.get_session_maker(company)
        if not session_maker:
            raise ConnectionError("Database connection not configured for this company.")
        
        async with session_maker() as session:
            yield session

# Singleton instance
external_connection_manager = ExternalConnectionManager()
