from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid
import os

from app.repository.company_repository import company_repository
from app.models import user_model
from app.schemas import user_schema, company_schema
from app.core.config import settings

async def get_company_users_by_admin_service(
    db: AsyncSession,
    current_user: user_model.Users
) -> List[user_schema.User]:
    result = await db.execute(
        select(user_model.Users).filter(user_model.Users.company_id == current_user.company_id)
    )
    users = result.scalars().all()
    return users

async def get_company_by_user_service(
    db: AsyncSession,
    current_user: user_model.Users
) -> company_schema.Company:
    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this user.")
    return db_company

async def get_company_users_paginated(
    db: AsyncSession,
    company_id: int,
    skip: int,
    limit: int,
    page: int,
    username: Optional[str] = None
) -> user_schema.PaginatedUserResponse:
    users, total_users = await company_repository.get_company_users_paginated(
        db=db,
        company_id=company_id,
        skip=skip,
        limit=limit,
        username=username
    )
    total_pages = (total_users + limit - 1) // limit
    return user_schema.PaginatedUserResponse(
        users=users,
        total_users=total_users,
        current_page=page,
        total_pages=total_pages
    )

async def update_company_by_admin_service(
    db: AsyncSession,
    current_user: user_model.Users,
    name: Optional[str],
    code: Optional[str],
    address: Optional[str],
    logo_file: Optional[UploadFile],
    pic_phone_number: Optional[str]
) -> company_schema.Company:
    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this admin.")

    logo_path_to_update = db_company.logo_s3_path

    if logo_file and logo_file.filename:
        UPLOAD_DIR = "static/company_logos"
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        file_extension = os.path.splitext(logo_file.filename)[1]
        logo_uuid = str(uuid.uuid4())
        filename = f"{logo_uuid}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        try:
            # Save new logo
            content = await logo_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            logo_path_to_update = f"/{file_path}"

            # Delete old logo if it exists
            if db_company.logo_s3_path:
                old_file_path = db_company.logo_s3_path.lstrip('/')
                if os.path.exists(old_file_path) and old_file_path != file_path:
                    os.remove(old_file_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload logo: {e}")

    company_update = company_schema.CompanyUpdate(
        name=name,
        code=code,
        address=address,
        logo_s3_path=logo_path_to_update,
        pic_phone_number=pic_phone_number
    )

    updated_company = await company_repository.update_company(db, current_user.company_id, company_update)
    if not updated_company:
        raise HTTPException(status_code=500, detail="Failed to update company in database.")

    return updated_company