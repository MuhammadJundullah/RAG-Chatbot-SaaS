from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid
import os
from botocore.exceptions import ClientError

from app.repository import company_repository, division_repository
from app.models import user_model
from app.core.dependencies import get_current_company_admin, get_db
from app.schemas import user_schema, company_schema
from app.services import user_service
from app.core.s3_client import s3_client_manager
from app.core.config import settings

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

# mendapatkan data users dari satu company 
@router.get("/users", response_model=List[user_schema.User])
async def read_company_users(
    db: AsyncSession = Depends(get_db),
    current_user: user_model.Users = Depends(get_current_company_admin)
):
    """
    Get a list of all users in the admin's company.
    Accessible only by the company's admin.
    """
    result = await db.execute(
        select(user_model.Users).filter(user_model.Users.company_id == current_user.company_id)
    )
    users = result.scalars().all()
    return users

@router.get("/me", response_model=company_schema.Company)
async def read_my_company(
    db: AsyncSession = Depends(get_db),
    current_user: user_model.Users = Depends(get_current_company_admin)
):
    """
    Get the current admin's company data.
    Accessible only by the company's admin.
    """
    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this admin.")
    return db_company

# register employee
@router.post("/employees/register", response_model=user_schema.User, status_code=status.HTTP_201_CREATED)
async def register_employee_by_company_admin(
    employee_data: user_schema.EmployeeRegistrationByAdmin,
    current_admin: user_model.Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Register a new employee for the admin's company.
    Accessible only by the company's admin.
    """
    if employee_data.division_id:
        division = await division_repository.get_division(db, employee_data.division_id)
        if not division or division.company_id != current_admin.company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Division not found or does not belong to your company."
            )

    try:
        new_employee = await user_service.register_employee_by_admin(
            db, employee_data=employee_data, company_id=current_admin.company_id
        )
        return new_employee
    except user_service.UserRegistrationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=e.detail,
        )

@router.put("/me", response_model=company_schema.Company)
async def update_my_company(
    name: Optional[str] = Form(None),
    code: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    logo_file: UploadFile = File(None),
    current_user: user_model.Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Update the current admin's company data, including logo upload to S3.
    Accessible only by the company's admin.
    """
    company_update = company_schema.CompanyUpdate(
        name=name,
        code=code,
        address=address,
        logo_s3_path=None # This will be set later if a logo_file is provided
    )

    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this admin.")

    print(f"[DEBUG] Received company_update: {company_update.model_dump()}")

    s3_client = await s3_client_manager.get_client()
    new_logo_s3_path = None

    if logo_file:
        if not logo_file.filename:
            raise HTTPException(status_code=400, detail="No logo file name provided.")
        
        # Generate a unique S3 key for the new logo
        file_extension = os.path.splitext(logo_file.filename)[1]
        logo_uuid = str(uuid.uuid4())
        s3_key = f"company_logos/{current_user.company_id}/{logo_uuid}{file_extension}"
        full_public_logo_url = f"{settings.PUBLIC_S3_BASE_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"

        try:
            # Upload new logo to S3 using the S3 key
            await s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=await logo_file.read(),
                ContentType=logo_file.content_type
            )
            company_update.logo_s3_path = full_public_logo_url

            # Delete old logo from S3 if it exists and is different
            if db_company.logo_s3_path:
                # Extract the S3 key from the old full URL for deletion
                old_s3_key = db_company.logo_s3_path.replace(f"{settings.PUBLIC_S3_BASE_URL}/", "")

                # Only delete if the old key is different from the new key
                if old_s3_key != s3_key:
                    try:
                        await s3_client.delete_objects(
                            Bucket=settings.S3_BUCKET_NAME,
                            Delete={
                                "Objects": [
                                    {"Key": old_s3_key}
                                ]
                            }
                        )
                        print(f"[Company Update] Deleted old logo from S3: {old_s3_key}")
                    except ClientError as e:
                        if e.response['Error']['Code'] not in ['404', 'NoSuchKey']:
                            raise e
                        print(f"[Company Update] Warning: Old S3 logo not found during deletion, proceeding. Key: {old_s3_key}")

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload logo to S3: {e}")

    updated_company = await company_repository.update_company(db, current_user.company_id, company_update)
    if not updated_company:
        raise HTTPException(status_code=500, detail="Failed to update company in database.")

    return updated_company