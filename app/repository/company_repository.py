from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import distinct
from app.models import company_model, user_model
from app.schemas import company_schema
from app.repository.base_repository import BaseRepository, ModelType, CreateSchemaType, UpdateSchemaType
from typing import Optional, List, Type

class CompanyRepository(BaseRepository[company_model.Company]):
    def __init__(self):
        super().__init__(company_model.Company)

    async def get_company(self, db: AsyncSession, company_id: int) -> Optional[company_model.Company]:
        return await self.get(db, company_id)

    async def get_company_by_name(self, db: AsyncSession, name: str) -> Optional[company_model.Company]:
        result = await db.execute(select(self.model).filter(self.model.name == name))
        return result.scalar_one_or_none()

    async def get_company_by_code(self, db: AsyncSession, code: str) -> Optional[company_model.Company]:
        result = await db.execute(select(self.model).filter(self.model.code == code))
        return result.scalar_one_or_none()

    async def get_companies(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[company_model.Company]:
        return await self.get_multi(db, skip=skip, limit=limit)

    async def get_active_companies(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[company_model.Company]:
        """Gets a list of companies that are active."""
        result = await db.execute(
            select(self.model).filter(self.model.is_active == True).offset(skip).limit(limit)
        )
        return result.scalars().all()

    async def is_company_active(self, db: AsyncSession, company_id: int) -> bool:
        """Checks if a company is active."""
        company = await self.get(db, company_id)
        return company and company.is_active

    async def get_pending_companies(self, db: AsyncSession, skip: int = 0, limit: int = 100) -> List[company_model.Company]:
        """Gets a list of companies that are not active (pending approval)."""
        result = await db.execute(
            select(self.model).filter(self.model.is_active == False).offset(skip).limit(limit)
        )
        pending_companies = result.scalars().all()
        print(f"[DEBUG get_pending_companies] Pending companies found: {[c.id for c in pending_companies]}")
        return pending_companies

    async def approve_company(self, db: AsyncSession, company_id: int):
        """Activates a company by setting its is_active status to True."""
        company = await self.get(db, company_id)
        if not company:
            return None

        if company.is_active:
            return "already_active"
        else:
            company.is_active = True
            db.add(company)
            await db.commit()
            await db.refresh(company)
            return "approved"

    async def reject_company(self, db: AsyncSession, company_id: int):
        """Rejects a company registration by deleting the company and its admin."""
        company = await self.get(db, company_id)
        if not company:
            return None

        admin_user_result = await db.execute(
            select(user_model.Users)
            .filter(user_model.Users.company_id == company_id, user_model.Users.role == 'admin')
        )
        admin_user = admin_user_result.scalar_one_or_none()

        if admin_user:
            await db.delete(admin_user)
        
        await db.delete(company)
        await db.commit()
        return company

    async def update_company(self, db: AsyncSession, company_id: int, company_update: company_schema.CompanyUpdate) -> Optional[company_model.Company]:
        """Updates an existing company's details."""
        db_company = await self.get(db, company_id)
        if db_company:
            update_data = company_update.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                if value is None and key in ["name", "code"]:
                    continue
                setattr(db_company, key, value)
            
            db.add(db_company)
            await db.commit()
            await db.refresh(db_company)

            if db_company.name is None or db_company.code is None:
                from fastapi import HTTPException, status
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Company data integrity error: 'name' or 'code' is missing after update."
                )

        return db_company

    async def create_company(self, db: AsyncSession, company: company_schema.CompanyCreate) -> company_model.Company:
        # This method is kept for now as company_service.py directly passes company_model.Company object
        # rather than a schema. If company_service is updated to pass a schema, this can be replaced
        # by super().create(db, company_schema.CompanyCreate.model_validate(company))
        db_company = self.model(
            name=company.name,
            code=company.code,
            logo_s3_path=company.logo_s3_path,
            address=company.address,
            is_active=company.is_active
        )
        db.add(db_company)
        await db.commit()
        await db.refresh(db_company)
        return db_company

company_repository = CompanyRepository()