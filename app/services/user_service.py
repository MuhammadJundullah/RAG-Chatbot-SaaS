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
    # Business Logic: Check if user already exists by email or username
    existing_user_by_email = await user_repository.get_user_by_email(db, email=user_data.email)
    if existing_user_by_email:
        raise UserRegistrationError("Email is already registered.")
    
    # For initial admin registration, use email as username if username is not provided
    username_to_use = user_data.username if user_data.username else user_data.email
    existing_user_by_username = await user_repository.get_user_by_username(db, username=username_to_use)
    if existing_user_by_username:
        raise UserRegistrationError("Username is already registered.")

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
            username=username_to_use,
            password=hashed_password,
            pic_phone_number=user_data.pic_phone_number,
            role="admin",
            company_id=new_company_obj.id,
            is_active_in_company=False
        )
    else:
        raise UserRegistrationError("Invalid registration data: only new company registration is allowed via this endpoint.")

    # Data Layer: Save the new user to the database
    return await user_repository.create_user(db, user=db_user)

async def register_employee_by_admin(db: AsyncSession, employee_data: user_schema.EmployeeRegistrationByAdmin, company_id: int):
    existing_user_by_email = await user_repository.get_user_by_email(db, email=employee_data.email)
    if existing_user_by_email:
        raise UserRegistrationError("Email is already registered.")
    
    existing_user_by_username = await user_repository.get_user_by_username(db, username=employee_data.username)
    if existing_user_by_username:
        raise UserRegistrationError("Username is already registered.")

    hashed_password = get_password_hash(employee_data.password)

    db_user = user_model.Users(
        name=employee_data.name,
        email=employee_data.email,
        username=employee_data.username,
        password=hashed_password,
        role="employee",
        company_id=company_id,
        is_active_in_company=True,
        Divisionid=employee_data.division_id
    )

    return await user_repository.create_user(db, user=db_user)

async def authenticate_user(db: AsyncSession, password: str, email: Optional[str] = None, username: Optional[str] = None) -> Optional[user_model.Users]:
    """
    Authenticates a user by email or username and password.

    - Fetches the user by email or username.
    - Verifies the password.
    - Checks if the user account is active and authorized for the given role.

    Returns the user object if authentication is successful, otherwise None.
    """
    user = None
    if username:
        user = await user_repository.get_user_by_username(db, username=username)
    elif email:
        user = await user_repository.get_user_by_email(db, email=email)
    
    if not user or not verify_password(password, user.password):
        return None

    # Superadmin specific check
    if user.role == 'super_admin':
        return user

    # Company admin/employee specific checks
    if user.role in ['admin', 'employee']:
        if not user.is_active_in_company:
            return None
        return user
        
    return None
