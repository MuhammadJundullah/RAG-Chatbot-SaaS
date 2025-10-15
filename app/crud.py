from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
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

# --- User & Company Registration CRUD ---

async def register_user(db: AsyncSession, user_data: schemas.UserRegistration):
    """
    Registers a new user. Can either create a new company or assign to an existing one.
    """
    # Check if user already exists
    existing_user = await get_user_by_email(db, email=user_data.email)
    if existing_user:
        return None

    hashed_password = get_password_hash(user_data.password)
    
    # Case 1: New Company Registration
    if user_data.company_name and user_data.company_code:
        # Check if company already exists
        existing_company = await get_company_by_name(db, name=user_data.company_name)
        if existing_company:
            return None

        # Create new company (pending approval)
        new_company = schema.Company(
            name=user_data.company_name,
            code=user_data.company_code
        )
        db.add(new_company)
        await db.flush() # Use flush to get the new company ID before committing

        # Create new user as company admin
        db_user = schema.Users(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            role="admin",
            company_id=new_company.id,
            is_active_in_company=False, # Admin must be approved by super admin
            is_super_admin=False
        )
    
    # Case 2: Employee joining existing company
    elif user_data.company_id is not None:
        # Check if company exists
        company = await get_company(db, company_id=user_data.company_id)
        if not company:
            return None

        db_user = schema.Users(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            role="employee",
            company_id=user_data.company_id,
            is_active_in_company=False, # Employee must be approved by company admin
            is_super_admin=False
        )
    else:
        # Invalid data
        return None

    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

# --- Approval CRUD ---

async def get_pending_companies(db: AsyncSession, skip: int = 0, limit: int = 100):
    # Subquery to find company IDs of inactive admin users
    inactive_admin_company_ids = (
        select(schema.Users.company_id)
        .filter(schema.Users.role == 'admin', schema.Users.is_active_in_company == False)
        .distinct()
    )

    # Main query to get the company objects
    result = await db.execute(
        select(schema.Company)
        .filter(schema.Company.id.in_(inactive_admin_company_ids))
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

async def approve_company(db: AsyncSession, company_id: int):
    # Find the company to ensure it exists and we can return it
    company = await get_company(db, company_id=company_id)
    if not company:
        return None

    # Find and activate the admin of that company
    admin_user_result = await db.execute(
        select(schema.Users)
        .filter(schema.Users.company_id == company_id, schema.Users.role == 'admin')
    )
    admin_user = admin_user_result.scalar_one_or_none()

    if admin_user and not admin_user.is_active_in_company:
        admin_user.is_active_in_company = True
        db.add(admin_user)
        await db.commit()
        await db.refresh(admin_user)

    return company

async def get_pending_employees(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100):
    result = await db.execute(
        select(schema.Users)
        .filter(schema.Users.company_id == company_id)
        .filter(schema.Users.is_active_in_company == False)
        .offset(skip).limit(limit)
    )
    return result.scalars().all()

async def approve_employee(db: AsyncSession, user_id: int):
    user = await get_user(db, user_id=user_id)
    if not user:
        return None
    user.is_active_in_company = True
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


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
        .filter(schema.Division.company_id == company_id)
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()

# --- User CRUD ---

async def get_user(db: AsyncSession, user_id: int):
    result = await db.execute(select(schema.Users).filter(schema.Users.id == user_id))
    return result.scalar_one_or_none()

async def get_user_by_email(db: AsyncSession, email: str):
    result = await db.execute(
        select(schema.Users)
        .options(joinedload(schema.Users.company))
        .filter(schema.Users.email == email)
    )
    return result.scalar_one_or_none()

async def get_users(db: AsyncSession, skip: int = 0, limit: int = 100):
    result = await db.execute(select(schema.Users).offset(skip).limit(limit))
    return result.scalars().all()




async def get_pending_users_by_company(db: AsyncSession, company_id: int):
    result = await db.execute(
        select(schema.Users)
        .filter(schema.Users.company_id == company_id)
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
        query = query.filter(schema.Chatlogs.company_id == company_id)
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
