from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from app.schemas import user_schema
from app.repository.user_repository import user_repository
from app.repository.company_repository import company_repository
from app.utils.security import get_password_hash, verify_password
from app.models import user_model, company_model
from app.core.config import settings
import os
from sqlalchemy.exc import IntegrityError
import logging
from datetime import datetime, timedelta

from app.utils.generators import generate_company_code, generate_reset_token
from app.utils.email_sender import send_brevo_email
from app.utils.file_manager import save_uploaded_file, delete_static_file
from app.modules.subscription.service import subscription_service
from sqlalchemy import func, select

class UserRegistrationError(Exception):
    """Custom exception for registration errors."""
    def __init__(self, detail: str):
        self.detail = detail

class EmployeeDeletionError(Exception):
    """Custom exception for employee deletion errors."""
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code

class EmployeeUpdateError(Exception):
    """Custom exception for employee update errors."""
    def __init__(self, detail: str, status_code: int = 400):
        self.detail = detail
        self.status_code = status_code

async def register_user(db: AsyncSession, user_data: user_schema.UserRegistration):
    """
    Orchestrates the business logic for registering a new user.
    Can either create a new company or assign to an existing one.
    """
    # Business Logic: Check if username already exists
    company_email_to_use = user_data.company_email or user_data.email
    username_to_use = user_data.username if user_data.username else company_email_to_use
    existing_user_by_username = await user_repository.get_user_by_username(db, username=username_to_use)
    if existing_user_by_username:
        raise UserRegistrationError("Username is already registered.")

    hashed_password = get_password_hash(user_data.password)
    
    # Business Logic: New Company Registration
    if user_data.company_name:
        # Business Logic: Check if company name/email already exists
        existing_company = await company_repository.get_company_by_name(db, name=user_data.company_name)
        if existing_company:
            raise UserRegistrationError("Company name is already registered.")
        # Gunakan email input sebagai company_email (Users.email tidak diisi)
        existing_company_email = await company_repository.get_company_by_email(db, company_email=company_email_to_use)
        if existing_company_email:
            raise UserRegistrationError("Company email is already registered.")

        # Data Layer: Create new company object
        company_code = generate_company_code() # Use helper
        new_company_obj = company_model.Company(
            name=user_data.company_name,
            code=company_code,
            pic_phone_number=user_data.pic_phone_number,
            company_email=company_email_to_use,
        )
        db.add(new_company_obj)
        await db.flush()  

        # Data Layer: Create new user object as company admin
        db_user = user_model.Users(
            name=user_data.name,
            username=username_to_use,
            password=hashed_password,
            role="admin",
            company_id=new_company_obj.id
        )
    else:
        raise UserRegistrationError("Invalid registration data: only new company registration is allowed via this endpoint.")

    # Data Layer: Save the new user to the database
    return await user_repository.create_user(db, user=db_user)

async def register_employee_by_admin(db: AsyncSession, employee_data: user_schema.EmployeeRegistrationByAdmin, company_id: int, current_user: user_model.Users, profile_picture_file: UploadFile = None):
    """
    Registers a new employee by an admin, including uploading a profile picture to the local server.
    Handles potential username uniqueness violations from the database.
    If a division name is provided and the division does not exist, it will be created.
    """
    # Check subscription user limit
    try:
        sub = await subscription_service.check_active_subscription(db, company_id=company_id)
        if sub.plan.max_users != -1:  # -1 means unlimited
            user_count_query = select(func.count(user_model.Users.id)).where(user_model.Users.company_id == company_id)
            result = await db.execute(user_count_query)
            user_count = result.scalar_one()

            if user_count >= sub.plan.max_users:
                raise UserRegistrationError(f"Cannot add new employee. The maximum user limit of {sub.plan.max_users} for the '{sub.plan.name}' plan has been reached.")
    except HTTPException as e:
        # If subscription is not active or found, prevent registration
        raise UserRegistrationError(f"Cannot add new employee: {e.detail}")
        
    existing_user_by_username = await user_repository.get_user_by_username(db, username=employee_data.username)
    if existing_user_by_username:
        raise UserRegistrationError("Username is already registered.")

    hashed_password = get_password_hash(employee_data.password)

    profile_picture_url = None
    if profile_picture_file and profile_picture_file.filename:
        UPLOAD_DIR = "static/employee_profiles"
        try:
            profile_picture_url = await save_uploaded_file(profile_picture_file, UPLOAD_DIR) # Use helper
        except Exception as e:
            logging.error(f"Failed to upload profile picture for employee {employee_data.username}: {e}")
            raise UserRegistrationError(f"Failed to upload profile picture: {e}")

    db_user = user_model.Users(
        name=employee_data.name,
        username=employee_data.username,
        password=hashed_password,
        role="employee",
        company_id=company_id,
        division=employee_data.division,
        profile_picture_url=profile_picture_url
    )

    try:
        # Attempt to create the user
        return await user_repository.create_user(db, user=db_user)
    except IntegrityError as e:
        # Catch database integrity errors, specifically username uniqueness violations
        if "ix_Users_username" in str(e):
            raise UserRegistrationError("Username already exists.")
        else:
            # Re-raise other integrity errors
            raise e
    except Exception as e:
        # Catch other potential errors during user creation
        logging.error(f"An unexpected error occurred during user creation: {e}")
        raise UserRegistrationError(f"An unexpected error occurred: {e}")

async def delete_employee_by_admin(db: AsyncSession, company_id: int, employee_id: int):
    """
    Deletes an employee if they belong to the specified company.
    """
    employee = await user_repository.get_user(db, user_id=employee_id)

    if not employee:
        raise EmployeeDeletionError(detail="Employee not found.", status_code=404)

    if employee.company_id != company_id:
        raise EmployeeDeletionError(detail="Not authorized to delete this employee.", status_code=403)

    # If employee has a profile picture, delete it from the local filesystem
    if employee.profile_picture_url:
        delete_static_file(employee.profile_picture_url) # Use helper

    await user_repository.delete_user(db, user_id=employee.id)
    return {"message": "Employee deleted successfully."}

async def update_employee_by_admin(
    db: AsyncSession, 
    company_id: int, 
    employee_id: int, 
    employee_data: user_schema.EmployeeUpdate, 
    profile_picture_file: UploadFile = None
) -> user_model.Users:
    """
    Updates an employee's data, including their profile picture stored locally.
    """
    employee = await user_repository.get_user(db, user_id=employee_id)

    if not employee or employee.company_id != company_id:
        raise EmployeeUpdateError(detail="Employee not found or not part of your company.", status_code=404)

    update_data = employee_data.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["password"] = get_password_hash(update_data["password"])

    if profile_picture_file and profile_picture_file.filename:
        UPLOAD_DIR = "static/employee_profiles"
        try:
            new_profile_picture_url = await save_uploaded_file(profile_picture_file, UPLOAD_DIR) # Use helper

            # Delete old profile picture if it exists
            if employee.profile_picture_url:
                delete_static_file(employee.profile_picture_url) # Use helper

            update_data["profile_picture_url"] = new_profile_picture_url
        except Exception as e:
            logging.error(f"Failed to upload profile picture for employee {employee.id}: {e}")
            raise EmployeeUpdateError(f"Failed to upload profile picture: {e}")

    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.commit()
    await db.refresh(employee)
    return employee

async def authenticate_user(
    db: AsyncSession,
    password: str,
    email: Optional[str] = None,
    username: Optional[str] = None,
) -> Optional[user_model.Users]:
    """
    Authenticates a user by email or username and password.
    - Fetches the user by email or username.
    - Verifies the password.
    - Checks if the user account is active and authorized for the given role.
    Returns the user object if authentication is successful, otherwise None.
    """
    user = None
    if email:
        company = await company_repository.get_company_by_email(db, company_email=email)
        if company:
            user = await user_repository.get_first_admin_by_company(db, company_id=company.id)
            if user and not user.company:
                user.company = company
    elif username:
        user = await user_repository.get_user_by_username(db, username=username)
        if user and user.role == "admin":
            return None
    
    if not user or not verify_password(password, user.password):
        return None

    # Superadmin specific check
    if user.role == 'super_admin':
        return user

    # Company admin/employee specific checks
    if user.role in ['admin', 'employee']:
        # Ensure company relationship is loaded for the user
        if not user.company or not user.company.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Company is inactive."
            )
        return user
        
    return None

async def request_password_reset(db: AsyncSession, email: str):
    """
    Initiates the password reset process for a user.
    Generates a token, stores it, and sends a reset email.
    """
    company = await company_repository.get_company_by_email(db, company_email=email)
    if not company or not company.company_email:
        # Mengembalikan pesan spesifik bahwa email tidak terdaftar.
        # Perlu diingat ini dapat membocorkan informasi tentang email yang terdaftar.
        logging.warning(f"Password reset requested for non-existent company email: {email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email company tidak terdaftar.",
        )

    user = await user_repository.get_first_admin_by_company(db, company_id=company.id)
    if not user:
        logging.warning(f"Password reset requested for company without admin: {company.id}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin perusahaan tidak ditemukan.",
        )

    if not user.is_active:
        logging.warning(f"Password reset requested for inactive user: {user.username}")
        return {"message": "Jika akun dengan email tersebut ada, tautan reset kata sandi telah dikirim.", "code": 400}

    # Generate token and set expiry
    token = generate_reset_token() # Use helper
    # Menggunakan durasi token yang sama untuk reset token expiry
    expiry_time = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) 

    user.reset_token = token
    user.reset_token_expiry = expiry_time

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Prepare email content
    reset_link = f"{settings.APP_BASE_URL}auth/reset-password?token={token}&email={company.company_email}"
    
    # Fetch company name for personalization, if available
    company_name = user.company.name if user.company else "Platform Kami"

    html_content = f"""
    <html>
    <body>
        <p>Halo {user.name or user.username},</p>
        <p>Kami menerima permintaan untuk mereset kata sandi Anda.</p>
        <p>Silakan klik tautan berikut untuk mengatur kata sandi baru Anda:</p>
        <p><a href="{reset_link}" style="color: #007bff; text-decoration: none;">Reset Kata Sandi</a></p>
        <p>Tautan ini akan kedaluwarsa dalam {settings.ACCESS_TOKEN_EXPIRE_MINUTES} menit.</p>
        <p>Jika Anda tidak meminta reset kata sandi, mohon abaikan email ini.</p>
        <p>Terima kasih,<br>Tim {settings.APP_NAME}</p>
    </body>
    </html>
    """
    subject = f"Reset Kata Sandi Anda untuk {company_name}"

    # Kirim email menggunakan Brevo
    try:
        await send_brevo_email( 
            to_email=company.company_email,
            subject=subject,
            html_content=html_content
        )
        return {"code": 200, "message": "Jika akun dengan email tersebut ada, tautan reset kata sandi telah dikirim."}
    except HTTPException as e:
        # Tangani HTTPException yang dilempar oleh send_brevo_email
        raise e
    except Exception as e:
        logging.error(f"An unexpected error occurred during password reset email sending to {company.company_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan tak terduga saat mengirim email reset kata sandi."
        )


async def reset_password(db: AsyncSession, email: str, token: str, new_password: str):
    """
    Resets the user's password after token verification.
    """
    company = await company_repository.get_company_by_email(db, company_email=email)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tautan reset kata sandi tidak valid atau sudah kedaluwarsa.",
        )

    user = await user_repository.get_first_admin_by_company(db, company_id=company.id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tautan reset kata sandi tidak valid atau sudah kedaluwarsa.",
        )

    # Verifikasi token dan expiry
    if user.reset_token != token or datetime.utcnow() > user.reset_token_expiry:
        # Hapus token yang tidak valid dari pengguna untuk mencegah upaya penggunaan ulang
        user.reset_token = None
        user.reset_token_expiry = None
        db.add(user)
        await db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tautan reset kata sandi tidak valid atau sudah kedaluwarsa.",
        )

    # Hash dan update password
    hashed_password = get_password_hash(new_password)
    user.password = hashed_password

    # Hapus token dan expiry setelah reset berhasil
    user.reset_token = None
    user.reset_token_expiry = None

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return {"code": 200, "message": "Kata sandi berhasil direset."}
