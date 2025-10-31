from fastapi import HTTPException, status, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid
import os
from botocore.exceptions import ClientError

from app.repository.company_repository import company_repository
from app.repository.division_repository import division_repository
from app.models import user_model
from app.schemas import user_schema, company_schema
from app.services import user_service
from app.core.s3_client import s3_client_manager
from app.core.config import settings

async def get_company_users_service(
    db: AsyncSession,
    current_user: user_model.Users
) -> List[user_schema.User]:
    result = await db.execute(
        select(user_model.Users).filter(user_model.Users.company_id == current_user.company_id)
    )
    users = result.scalars().all()
    return users

async def get_my_company_service(
    db: AsyncSession,
    current_user: user_model.Users
) -> company_schema.Company:
    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this admin.")
    return db_company

async def register_employee_by_company_admin_service(
    db: AsyncSession,
    employee_data: user_schema.EmployeeRegistrationByAdmin,
    current_admin: user_model.Users
) -> user_schema.User:
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

async def update_my_company_service(
    db: AsyncSession,
    current_user: user_model.Users,
    name: Optional[str],
    code: Optional[str],
    address: Optional[str],
    logo_file: Optional[UploadFile]
) -> company_schema.Company:
    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this admin.")

    # Initialize logo_s3_path with the existing logo path
    logo_s3_path_to_update = db_company.logo_s3_path

    s3_client = await s3_client_manager.get_client()

    if logo_file and logo_file.filename:
        
        file_extension = os.path.splitext(logo_file.filename)[1]
        logo_uuid = str(uuid.uuid4())
        s3_key = f"company_logos/{current_user.company_id}/{logo_uuid}{file_extension}"
        full_public_logo_url = f"{settings.PUBLIC_S3_BASE_URL}/{settings.S3_BUCKET_NAME}/{s3_key}"

        try:
            await s3_client.put_object(
                Bucket=settings.S3_BUCKET_NAME,
                Key=s3_key,
                Body=await logo_file.read(),
                ContentType=logo_file.content_type
            )
            logo_s3_path_to_update = full_public_logo_url # Update with new logo path

            if db_company.logo_s3_path:
                old_s3_key = db_company.logo_s3_path.replace(f"{settings.PUBLIC_S3_BASE_URL}/{settings.S3_BUCKET_NAME}/", "")

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

    company_update = company_schema.CompanyUpdate(
        name=name,
        code=code,
        address=address,
        logo_s3_path=logo_s3_path_to_update # Use the determined logo path
    )

    print(f"[DEBUG] Received company_update: {company_update.model_dump()}")

    updated_company = await company_repository.update_company(db, current_user.company_id, company_update)
    if not updated_company:
        raise HTTPException(status_code=500, detail="Failed to update company in database.")

    return updated_company