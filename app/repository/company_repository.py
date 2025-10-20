from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import company_model

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

async def approve_company(db: AsyncSession, company_id: int):
    # Find the company to ensure it exists and we can return it
    company = await get_company(db, company_id=company_id)
    if not company:
        return None

    # Find and activate the admin of that company
    # This part needs to import user_model and user_repository
    from app.models import user_model
    from app.repository import user_repository

    admin_user_result = await db.execute(
        select(user_model.Users)
        .filter(user_model.Users.company_id == company_id, user_model.Users.role == 'admin')
    )
    admin_user = admin_user_result.scalar_one_or_none()

    if admin_user and not admin_user.is_active_in_company:
        admin_user.is_active_in_company = True
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

    return company