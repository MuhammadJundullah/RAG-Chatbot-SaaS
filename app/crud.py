from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
from datetime import date
from app.database import schema
from app.models import schemas
from app.utils.security import get_password_hash

# --- Company CRUD ---

async def get_company(db: AsyncSession, company_id: int):
    result = await db.execute(select(schema.Company).filter(schema.Company.id == company_id))
    return result.scalar_one_or_none()

async def get_company_by_name(db: AsyncSession, name: str):
    result = await db.execute(select(schema.Company).filter(schema.Company.name == name))
    return result.scalar_one_or_none()

async def get_company_by_code(db: AsyncSession, code: str):
    result = await db.execute(select(schema.Company).filter(schema.Company.code == code))
    return result.scalar_one_or_none()

async def get_companies(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(schema.Company).offset(skip).limit(limit))
    return result.scalars().all()

async def create_company(db: AsyncSession, company: schemas.CompanyCreate):
    db_company = schema.Company(**company.model_dump())
    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    return db_company


async def create_company_and_admin(db: AsyncSession, data: schemas.CompanyAdminCreate):
    # Create the company
    company_data = schemas.CompanyCreate(
        name=data.company_name,
        code=data.company_code,
        logo=data.company_logo
    )
    db_company = await create_company(db, company=company_data)

    # Create the admin user
    admin_data = schemas.UserCreate(
        name=data.admin_name,
        email=data.admin_email,
        password=data.admin_password,
        role="admin",
        status="active",
        Companyid=db_company.id
    )
    db_user = await create_user(db, user=admin_data)

    return db_company, db_user

# --- Division CRUD ---

async def create_division(db: AsyncSession, division: schemas.DivisionCreate):
    db_division = schema.Division(**division.model_dump())
    db.add(db_division)
    await db.commit()
    await db.refresh(db_division)
    return db_division

async def get_division(db: AsyncSession, division_id: int):
    result = await db.execute(select(schema.Division).filter(schema.Division.id == division_id))
    return result.scalar_one_or_none()

async def get_divisions_by_company(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(schema.Division)
        .filter(schema.Division.Companyid == company_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

# --- User CRUD ---

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(schema.Users).filter(schema.Users.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(select(schema.Users).filter(schema.Users.email == email))
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(schema.Users).offset(skip).limit(limit))
    return result.scalars().all()

async def create_user(db: AsyncSession, user: schemas.UserCreate):
    hashed_password = get_password_hash(user.password)
    db_user = schema.Users(
        name=user.name,
        email=user.email,
        password=hashed_password,
        status=user.status,
        role=user.role,
        Companyid=user.Companyid,
        Divisionid=user.Divisionid,
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user


async def get_pending_users_by_company(db: AsyncSession, company_id: int):
    result = await db.execute(
        select(schema.Users)
        .filter(schema.Users.Companyid == company_id)
        .filter(schema.Users.status == "pending_approval")
    )
    return result.scalars().all()


async def update_user_status(db: AsyncSession, user: schema.Users, status: str):
    user.status = status
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user





async def delete_user(db: AsyncSession, user: schema.Users):
    await db.delete(user)
    await db.commit()

# --- Document CRUD ---

async def get_document(db: AsyncSession, document_id: int):
    result = await db.execute(select(schema.Documents).filter(schema.Documents.id == document_id))
    return result.scalar_one_or_none()

async def get_documents(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(schema.Documents).offset(skip).limit(limit))
    return result.scalars().all()



async def delete_document(db: AsyncSession, document: schema.Documents):
    await db.delete(document)
    await db.commit()

# --- Chatlog CRUD ---

async def create_chatlog(db: AsyncSession, chatlog: schemas.ChatlogCreate):
    db_chatlog = schema.Chatlogs(**chatlog.model_dump())
    db.add(db_chatlog)
    await db.commit()
    await db.refresh(db_chatlog)
    return db_chatlog

async def get_chatlogs(
    db: AsyncSession,
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
):
    query = select(schema.Chatlogs)
    if company_id:
        query = query.filter(schema.Chatlogs.Companyid == company_id)
    if user_id:
        query = query.filter(schema.Chatlogs.UsersId == user_id)
    if start_date:
        query = query.filter(schema.Chatlogs.created_at >= start_date)
    if end_date:
        query = query.filter(schema.Chatlogs.created_at <= end_date)
    
    result = await db.execute(query.offset(skip).limit(limit))
    return result.scalars().all()

# --- Embedding CRUD ---

async def create_embedding(db: AsyncSession, embedding: schemas.EmbeddingCreate):
    db_embedding = schema.Embeddings(**embedding.model_dump())
    db.add(db_embedding)
    await db.commit()
    await db.refresh(db_embedding)
    return db_embedding
