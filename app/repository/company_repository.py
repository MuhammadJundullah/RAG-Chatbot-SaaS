from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import distinct
from app.models import company_model, user_model
from app.schemas import company_schema

async def get_company(db: AsyncSession, company_id: int):
    result = await db.execute(select(company_model.Company).filter(company_model.Company.id == company_id))
    return result.scalar_one_or_none()

async def get_company_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(company_model.Company).filter(company_model.Company.name == name))
    return result.scalar_one_or_none()

async def get_company_by_code(db: AsyncSession, code: str):
    result = await db.execute(select(company_model.Company).filter(company_model.Company.code == code))
    return result.scalar_one_or_none()

async def get_companies(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(company_model.Company).offset(skip).limit(limit))
    return result.scalars().all()

async def get_active_companies(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Gets a list of companies that are active."""
    result = await db.execute(
        select(company_model.Company).filter(company_model.Company.is_active == True).offset(skip).limit(limit)
    )
    return result.scalars().all()

async def is_company_active(db: AsyncSession, company_id: int) -> bool:
    """Checks if a company is active."""
    company = await get_company(db, company_id=company_id)
    return company and company.is_active

async def get_pending_companies(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Gets a list of companies that are not active (pending approval)."""
    result = await db.execute(
        select(company_model.Company).filter(company_model.Company.is_active == False).offset(skip).limit(limit)
    )
    pending_companies = result.scalars().all()
    print(f"[DEBUG get_pending_companies] Pending companies found: {[c.id for c in pending_companies]}")
    return pending_companies

async def approve_company(db: AsyncSession, company_id: int):
    """Activates a company by setting its is_active status to True."""
    company = await get_company(db, company_id=company_id)
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

async def reject_company(db: AsyncSession, company_id: int):
    """Rejects a company registration by deleting the company and its admin."""
    company = await get_company(db, company_id=company_id)
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

async def update_company(db: AsyncSession, company_id: int, company_update: company_schema.CompanyUpdate) -> company_model.Company | None:
    """Updates an existing company's details."""
    db_company = await get_company(db, company_id)
    if db_company:
        update_data = company_update.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            # For non-nullable fields like 'name' and 'code', if the incoming value is None,
            # we skip updating it to None to preserve existing data.
            # For nullable fields like 'address' or 'logo_s3_path', None is a valid update.
            if value is None and key in ["name", "code"]:
                continue
            setattr(db_company, key, value)
        
        db.add(db_company)
        await db.commit()
        await db.refresh(db_company)

        # Ensure name and code are not None after refresh, as per Company schema requirements
        if db_company.name is None or db_company.code is None:
            # This indicates a data integrity issue in the database if these fields are expected to be non-nullable
            # For now, we raise an error to prevent ResponseValidationError
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Company data integrity error: 'name' or 'code' is missing after update."
            )

    return db_company