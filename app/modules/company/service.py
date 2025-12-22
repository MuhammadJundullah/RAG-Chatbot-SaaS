from fastapi import HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional
import uuid
import os

from app.repository.company_repository import company_repository
from app.repository import user_repository
from app.models import user_model, company_model
from app.schemas import user_schema, company_schema
from app.core.config import settings
from app.utils.security import get_password_hash

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
    search: Optional[str] = None
) -> user_schema.PaginatedUserResponse:
    users, total_users = await company_repository.get_company_users_paginated(
        db=db,
        company_id=company_id,
        skip=skip,
        limit=limit,
        search=search
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
    company_email: Optional[str],
    admin_name: Optional[str],
    admin_password: Optional[str],
    code: Optional[str],
    address: Optional[str],
    logo_file: Optional[UploadFile],
    pic_phone_number: Optional[str]
) -> (company_model.Company, user_model.Users):
    db_company = await company_repository.get_company(db, company_id=current_user.company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found for this admin.")

    # Update admin user details
    if admin_name:
        current_user.name = admin_name
    if admin_password:
        current_user.hashed_password = get_password_hash(admin_password)
    
    db.add(current_user)

    logo_path_to_update = db_company.logo_s3_path

    if logo_file and logo_file.filename:
        UPLOAD_DIR = "static/company_logos"
        os.makedirs(UPLOAD_DIR, exist_ok=True)

        file_extension = os.path.splitext(logo_file.filename)[1]
        logo_uuid = str(uuid.uuid4())
        filename = f"{logo_uuid}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        try:
            content = await logo_file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            logo_path_to_update = f"/{file_path}"

            if db_company.logo_s3_path:
                old_file_path = db_company.logo_s3_path.lstrip('/')
                if os.path.exists(old_file_path) and old_file_path != file_path:
                    os.remove(old_file_path)

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to upload logo: {e}")

    update_data = {
        "name": name,
        "company_email": company_email,
        "code": code,
        "address": address,
        "logo_s3_path": logo_path_to_update,
        "pic_phone_number": pic_phone_number
    }
    
    # Filter out None values so they don't overwrite existing data
    update_data_filtered = {k: v for k, v in update_data.items() if v is not None}

    for key, value in update_data_filtered.items():
        setattr(db_company, key, value)

    db.add(db_company)
    await db.commit()
    await db.refresh(db_company)
    await db.refresh(current_user)

    return db_company, current_user
