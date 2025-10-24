from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models import company_model, user_model

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
    """Activates the admin user of a company and returns a status."""
    company = await get_company(db, company_id=company_id)
    if not company:
        return None

    admin_user_result = await db.execute(
        select(user_model.Users)
        .filter(user_model.Users.company_id == company_id, user_model.Users.role == 'admin')
    )
    admin_user = admin_user_result.scalar_one_or_none()

    if admin_user:
        if admin_user.is_active_in_company:
            return "already_active"
        else:
            admin_user.is_active_in_company = True
            db.add(admin_user)
            await db.commit()
            await db.refresh(admin_user)
            return "approved"
    
    return None

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