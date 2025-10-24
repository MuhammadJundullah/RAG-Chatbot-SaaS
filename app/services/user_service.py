from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
import secrets
import string
from app.schemas import user_schema
from app.repository import user_repository, company_repository
from app.utils.security import get_password_hash, verify_password
from app.models import user_model, company_model

class UserRegistrationError(Exception):
    """Custom exception for registration errors."""
    def __init__(self, detail: str):
        self.detail = detail

def generate_company_code(length=6):
    """Generates a random, secure company code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

async def register_user(db: AsyncSession, user_data: user_schema.UserRegistration):
    """
    Orchestrates the business logic for registering a new user.
    Can either create a new company or assign to an existing one.
    """
    # Business Logic: Check if user already exists
    existing_user = await user_repository.get_user_by_email(db, email=user_data.email)
    if existing_user:
        raise UserRegistrationError("Email is already registered.")

    hashed_password = get_password_hash(user_data.password)
    
    # Business Logic: New Company Registration
    if user_data.company_name:
        # Business Logic: Check if company name already exists
        existing_company = await company_repository.get_company_by_name(db, name=user_data.company_name)
        if existing_company:
            raise UserRegistrationError("Company name is already registered.")

        # Data Layer: Create new company object
        company_code = generate_company_code()
        new_company_obj = company_model.Company(
            name=user_data.company_name,
            code=company_code
        )
        db.add(new_company_obj)
        await db.flush()  # Flush to get the new company ID before committing

        # Data Layer: Create new user object as company admin
        db_user = user_model.Users(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            pic_phone_number=user_data.pic_phone_number,
            role="admin",
            company_id=new_company_obj.id,
            is_active_in_company=False
        )
    
    # Business Logic: Employee joining existing company
    elif user_data.company_id is not None:
        # Business Logic: Check if company exists
        company = await company_repository.get_company(db, company_id=user_data.company_id)
        if not company:
            raise UserRegistrationError("Company ID not found.")

        # Data Layer: Create new user object as employee
        db_user = user_model.Users(
            name=user_data.name,
            email=user_data.email,
            password=hashed_password,
            role="employee",
            company_id=user_data.company_id,
            is_active_in_company=False
        )
    else:
        raise UserRegistrationError("Invalid registration data: provide either company details or a company ID.")

    # Data Layer: Save the new user to the database
    return await user_repository.create_user(db, user=db_user)

async def authenticate_user(db: AsyncSession, email: str, password: str) -> Optional[user_model.Users]:
    """
    Authenticates a user by email and password.

    - Fetches the user by email.
    - Verifies the password.
    - Checks if the user account is active.

    Returns the user object if authentication is successful, otherwise None.
    """
    user = await user_repository.get_user_by_email(db, email=email)
    
    # Business Logic: Validate user existence and password
    if not user or not verify_password(password, user.password):
        return None

    # Business Logic: Validate if user is active
    if not user.is_active_in_company:
        return None
        
    return user

async def authenticate_superadmin(db: AsyncSession, username: str, password: str) -> Optional[user_model.Users]:
    """
    Authenticates a superadmin by username and password.
    """
    user = await user_repository.get_user_by_username(db, username=username)
    
    if not user or not verify_password(password, user.password):
        return None

    if user.role != 'super_admin':
        return None
        
    return user
