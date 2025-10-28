from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from app.models import user_model, company_model

# --- User Repository ---

async def create_user(db: AsyncSession, user: user_model.Users) -> user_model.Users:
    """
    Adds a new user object to the database.
    """
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(user_model.Users).filter(user_model.Users.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(user_model.Users)
        .options(joinedload(user_model.Users.company))
        .filter(user_model.Users.email == email)
    )
    return result.scalar_one_or_none()

async def get_user_by_username(db: AsyncSession, username: str):
    result = await db.execute(
        select(user_model.Users)
        .options(joinedload(user_model.Users.company))
        .filter(user_model.Users.username == username)
    )
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(user_model.Users).offset(skip).limit(limit))
    return result.scalars().all()

async def update_user_status(db: AsyncSession, user: user_model.Users, status: str):
    user.status = status
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

async def delete_user(db: AsyncSession, user: user_model.Users):
    await db.delete(user)
    await db.commit()

# --- Approval Repository ---

async def get_pending_companies(db: AsyncSession, skip: int = 0, limit: int = 100):
    # Subquery to find company IDs of inactive admin users
    inactive_admin_company_ids = (
        select(user_model.Users.company_id)
        .filter(user_model.Users.role == 'admin', not user_model.Users.is_active_in_company)
        .distinct()
    )

    # Main query to get the company objects
    result = await db.execute(
        select(company_model.Company)
        .filter(company_model.Company.id.in_(inactive_admin_company_ids))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()
