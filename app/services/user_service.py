from sqlalchemy.ext.asyncio import AsyncSession
import secrets
import string
from typing import Optional
from fastapi import UploadFile, HTTPException, status
from app.schemas import user_schema
from app.repository.user_repository import user_repository
from app.repository.company_repository import company_repository
from app.utils.security import get_password_hash, verify_password
from app.models import user_model, company_model
from app.core.config import settings
from app.core.s3_client import s3_client_manager 
import os 
import uuid 
import io 
from sqlalchemy.exc import IntegrityError
import logging
from botocore.exceptions import ClientError
from datetime import datetime, timedelta 
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException

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

def generate_company_code(length=6):
    """Generates a random, secure company code."""
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

def generate_reset_token(length=32):
    """Generates a random, secure token for password reset."""
    alphabet = string.ascii_letters + string.digits
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
            code=company_code,
            pic_phone_number=user_data.pic_phone_number
        )
        db.add(new_company_obj)
        await db.flush()  # Flush to get the new company ID before committing

        # Data Layer: Create new user object as company admin
        db_user = user_model.Users(
            name=user_data.name,
            email=user_data.email,
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
    Registers a new employee by an admin, including uploading a profile picture to S3.
    Handles potential username uniqueness violations from the database.
    If a division name is provided and the division does not exist, it will be created.
    """
    existing_user_by_email = await user_repository.get_user_by_email(db, email=employee_data.email)
    if existing_user_by_email:
        raise UserRegistrationError("Email is already registered.")
    
    existing_user_by_username = await user_repository.get_user_by_username(db, username=employee_data.username)
    if existing_user_by_username:
        raise UserRegistrationError("Username is already registered.")

    hashed_password = get_password_hash(employee_data.password)

    profile_picture_url = None
    if profile_picture_file and profile_picture_file.filename:
        # Generate file extension and a unique identifier
        file_extension = os.path.splitext(profile_picture_file.filename)[1]
        logo_uuid = str(uuid.uuid4())
        
        # Construct the S3 key using a specific prefix for employee pictures
        s3_key = f"employee_profile_pictures/{company_id}/{logo_uuid}{file_extension}"
            
        try:
            # Read file content and create a BytesIO object
            file_content = await profile_picture_file.read()
            file_object = io.BytesIO(file_content)
            
            # Upload file to S3 using the enhanced upload_file method
            await s3_client_manager.upload_file(
                file_object=file_object,
                bucket_name=settings.S3_BUCKET_NAME,
                file_key=s3_key,
                content_type=profile_picture_file.content_type
            )
            profile_picture_url = f"https://1xg7ah.leapcellobj.com/{settings.S3_BUCKET_NAME}/{s3_key}"
        except Exception as e:
            logging.error(f"Failed to upload profile picture for employee {employee_data.email}: {e}")
            # Raise a user-friendly error if upload fails
            raise UserRegistrationError(f"Failed to upload profile picture: {e}")

    db_user = user_model.Users(
        name=employee_data.name,
        email=employee_data.email,
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

    # If employee has a profile picture, delete it from S3
    if employee.profile_picture_url:
        try:
            # Extract the S3 key from the URL
            # Assuming the URL format is https://1xg7ah.leapcellobj.com/{bucket_name}/{s3_key}
            # We need to remove the base URL and bucket name to get the s3_key
            base_url = f"https://1xg7ah.leapcellobj.com/{settings.S3_BUCKET_NAME}/"
            s3_key = employee.profile_picture_url.replace(base_url, "")
            await s3_client_manager.delete_file(bucket_name=settings.S3_BUCKET_NAME, file_key=s3_key)
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                logging.warning(f"Profile picture not found in S3 for employee {employee.id} (key: {s3_key}). Proceeding with user deletion.")
            else:
                logging.error(f"Failed to delete profile picture from S3 for employee {employee.id}: {e}")
        except Exception as e:
            logging.error(f"An unexpected error occurred during S3 profile picture deletion for employee {employee.id}: {e}")
            # Decide whether to raise an error or just log it. For now, we'll log and proceed with user deletion.

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
    Updates an employee's data, including their profile picture.
    """
    employee = await user_repository.get_user(db, user_id=employee_id)

    if not employee or employee.company_id != company_id:
        raise EmployeeUpdateError(detail="Employee not found or not part of your company.", status_code=404)

    update_data = employee_data.model_dump(exclude_unset=True)

    if "password" in update_data and update_data["password"]:
        update_data["password"] = get_password_hash(update_data["password"])

    if profile_picture_file and profile_picture_file.filename:
        file_extension = os.path.splitext(profile_picture_file.filename)[1]
        logo_uuid = str(uuid.uuid4())
        s3_key = f"employee_profile_pictures/{company_id}/{logo_uuid}{file_extension}"
        
        try:
            file_content = await profile_picture_file.read()
            file_object = io.BytesIO(file_content)
            
            await s3_client_manager.upload_file(
                file_object=file_object,
                bucket_name=settings.S3_BUCKET_NAME,
                file_key=s3_key,
                content_type=profile_picture_file.content_type
            )
            new_profile_picture_url = f"https://1xg7ah.leapcellobj.com/{settings.S3_BUCKET_NAME}/{s3_key}"

            if employee.profile_picture_url:
                base_url = f"https://1xg7ah.leapcellobj.com/{settings.S3_BUCKET_NAME}/"
                old_s3_key = employee.profile_picture_url.replace(base_url, "")
                await s3_client_manager.delete_file(bucket_name=settings.S3_BUCKET_NAME, file_key=old_s3_key)

            update_data["profile_picture_url"] = new_profile_picture_url
        except Exception as e:
            logging.error(f"Failed to upload profile picture for employee {employee.id}: {e}")
            raise EmployeeUpdateError(f"Failed to upload profile picture: {e}")

    for field, value in update_data.items():
        setattr(employee, field, value)

    await db.commit()
    await db.refresh(employee)
    return employee

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
        # Ensure company relationship is loaded for the user
        if not user.company or not user.company.is_active:
            return None
        return user
        
    return None

# --- Fungsi Pengiriman Email Brevo yang Diperbarui ---
async def send_brevo_email(to_email: str, subject: str, html_content: str):
    """
    Sends a transactional email using Brevo API.
    """
    # Konfigurasi API Key Brevo
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = settings.BREVO_API_KEY
    
    # Instantiate the TransactionalEmailsApi client
    api_client = sib_api_v3_sdk.ApiClient(configuration)
    transactional_api = sib_api_v3_sdk.TransactionalEmailsApi(api_client)

    # Tentukan detail pengirim
    # Mengambil dari environment variable atau menggunakan default
    sender_email = settings.DEFAULT_SENDER_EMAIL if settings.DEFAULT_SENDER_EMAIL else "noreply@yourdomain.com"
    # Menggunakan nama aplikasi dari settings jika ada, atau placeholder
    sender_name = getattr(settings, 'APP_NAME', 'SmartAI') 

    # Tentukan detail penerima
    to_recipient = [{"email": to_email, "name": to_email}] 

    # Tentukan konten email
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=to_recipient,
        subject=subject,
        html_content=html_content,
        sender={"email": sender_email, "name": sender_name},
        # Anda juga bisa menggunakan template_id untuk email yang lebih kompleks
        # template_id=1 # Contoh ID template
    )

    try:
        # Lakukan panggilan untuk mengirim email transaksional
        response = transactional_api.send_transac_email(send_smtp_email)
        logging.info(f"Email sent successfully to {to_email}. Response: {response}")
        # Objek response mungkin berisi 'messageId' atau yang serupa
    except ApiException as e:
        logging.error(f"Exception when calling Brevo API to send email to {to_email}: {e}")
        # Re-raise atau tangani exception sesuai kebutuhan
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Gagal mengirim email: {e.reason}"
        )
    except Exception as e:
        logging.error(f"An unexpected error occurred while sending email to {to_email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan tak terduga saat mengirim email."
        )
# --- Akhir Fungsi Pengiriman Email Brevo ---


async def request_password_reset(db: AsyncSession, email: str):
    """
    Initiates the password reset process for a user.
    Generates a token, stores it, and sends a reset email.
    """
    user = await user_repository.get_user_by_email(db, email=email)

    if not user:
        # Mengembalikan pesan spesifik bahwa email tidak terdaftar.
        # Perlu diingat ini dapat membocorkan informasi tentang email yang terdaftar.
        logging.warning(f"Password reset requested for non-existent email: {email}")
        return {"message": "Email tidak terdaftar."} # Pesan diubah sesuai permintaan

    if not user.is_active:
        logging.warning(f"Password reset requested for inactive user: {email}")
        return {"message": "Jika akun dengan email tersebut ada, tautan reset kata sandi telah dikirim."}

    # Generate token and set expiry
    token = generate_reset_token()
    # Menggunakan durasi token yang sama untuk reset token expiry
    expiry_time = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) 

    user.reset_token = token
    user.reset_token_expiry = expiry_time

    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Prepare email content
    reset_link = f"{settings.APP_BASE_URL}/auth/reset-password?token={token}&email={user.email}"
    
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
        <p>Terima kasih,<br>Tim SmartAI</p>
    </body>
    </html>
    """
    subject = f"Reset Kata Sandi Anda untuk {company_name}"

    # Kirim email menggunakan Brevo
    try:
        await send_brevo_email(
            to_email=user.email,
            subject=subject,
            html_content=html_content
        )
        return {"message": "Jika akun dengan email tersebut ada, tautan reset kata sandi telah dikirim."}
    except HTTPException as e:
        # Tangani HTTPException yang dilempar oleh send_brevo_email
        raise e
    except Exception as e:
        logging.error(f"An unexpected error occurred during password reset email sending to {user.email}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Terjadi kesalahan tak terduga saat mengirim email reset kata sandi."
        )


async def reset_password(db: AsyncSession, email: str, token: str, new_password: str):
    """
    Resets the user's password after token verification.
    """
    user = await user_repository.get_user_by_email(db, email=email)

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

    return {"message": "Kata sandi berhasil direset."}


# --- Fungsi yang sudah ada ---
# Pastikan fungsi-fungsi ini tetap ada di file yang sama.
# Untuk keringkasan, saya tidak menampilkannya lagi di sini.
# Contoh: register_user, authenticate_user, dll.