import secrets
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import schema
from app.models import schemas
from app.utils.security import get_password_hash, verify_password
from app.utils.encryption import encrypt_string

# --- User CRUD ---

async def get_user_by_username(db: AsyncSession, username: str) -> schema.User:
    result = await db.execute(select(schema.User).filter(schema.User.username == username))
    return result.scalar_one_or_none()

# --- Company CRUD ---

async def get_company_by_name(db: AsyncSession, name: str) -> schema.Company:
    result = await db.execute(select(schema.Company).filter(schema.Company.name == name))
    return result.scalar_one_or_none()

async def get_company_by_code(db: AsyncSession, code: str) -> schema.Company:
    result = await db.execute(select(schema.Company).filter(schema.Company.company_code == code))
    return result.scalar_one_or_none()

async def set_db_connection_string(db: AsyncSession, company: schema.Company, db_url: str) -> schema.Company:
    """Encrypts and saves the database connection string for a company."""
    company.encrypted_db_connection_string = encrypt_string(db_url)
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company

async def delete_db_connection_string(db: AsyncSession, company: schema.Company) -> schema.Company:
    """Sets the database connection string for a company to None."""
    company.encrypted_db_connection_string = None
    db.add(company)
    await db.commit()
    await db.refresh(company)
    return company

async def create_company_and_admin(db: AsyncSession, company_data: schemas.CompanyCreate) -> schema.Company:
    # Generate unique company code and a temporary secret
    company_code = str(uuid.uuid4().hex[:6].upper())
    company_secret = secrets.token_hex(24) # 48-character hex string, safe for bcrypt

    # Create Company
    db_company = schema.Company(
        name=company_data.name,
        company_code=company_code,
        company_secret=company_secret # Store raw secret
    )
    db.add(db_company)
    await db.flush() # Flush to get the company ID

    # Create Admin User for the company
    hashed_password = get_password_hash(company_data.admin_password)
    db_user = schema.User(
        username=company_data.admin_username,
        hashed_password=hashed_password,
        role=schema.UserRole.COMPANY_ADMIN,
        is_active=True, # Company admin is active by default
        company_id=db_company.id
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_company)
    # We should return the unhashed secret here one time for the admin to know
    db_company.unhashed_secret = company_secret
    return db_company

# --- Employee CRUD ---

async def create_employee(db: AsyncSession, employee_data: schemas.EmployeeCreate, company: schema.Company) -> schema.User:
    hashed_password = get_password_hash(employee_data.password)
    db_employee = schema.User(
        username=employee_data.username,
        hashed_password=hashed_password,
        role=schema.UserRole.EMPLOYEE,
        is_active=False, # Employee is not active by default
        company_id=company.id,
        division_id=employee_data.division_id
    )
    db.add(db_employee)
    await db.commit()
    await db.refresh(db_employee)
    return db_employee

# --- Division CRUD ---

async def create_division(db: AsyncSession, division_data: schemas.DivisionCreate, company_id: int) -> schema.Division:
    db_division = schema.Division(
        name=division_data.name,
        company_id=company_id
    )
    db.add(db_division)
    await db.commit()
    await db.refresh(db_division)
    return db_division

async def get_divisions_by_company(db: AsyncSession, company_id: int) -> list[schema.Division]:
    result = await db.execute(select(schema.Division).filter(schema.Division.company_id == company_id))
    return result.scalars().all()

async def get_division_by_id(db: AsyncSession, division_id: int) -> schema.Division:
    result = await db.execute(select(schema.Division).filter(schema.Division.id == division_id))
    return result.scalar_one_or_none()

async def update_division(db: AsyncSession, division: schema.Division, update_data: schemas.DivisionUpdate) -> schema.Division:
    """Updates a division's details."""
    for key, value in update_data.model_dump(exclude_unset=True).items():
        setattr(division, key, value)
    db.add(division)
    await db.commit()
    await db.refresh(division)
    return division

async def delete_division(db: AsyncSession, division: schema.Division):
    """Deletes a division."""
    await db.delete(division)
    await db.commit()
