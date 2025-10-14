from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils import auth
from app.utils.auth import get_current_user
from app.database.schema import Users

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)


@router.get("/", response_model=List[schemas.Company])
async def read_companies(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(db_manager.get_db_session)
):
    companies = await crud.get_companies(db, skip=skip, limit=limit)
    return companies


@router.get("/{company_id}", response_model=schemas.Company)
async def read_company(company_id: int, db: AsyncSession = Depends(db_manager.get_db_session)):
    db_company = await crud.get_company(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    return db_company

@router.get("/{company_id}/users/", response_model=List[schemas.User])
async def read_company_users(
    company_id: int, 
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: schema.Users = Depends(get_current_user)
):
    db_company = await crud.get_company(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    
    result = await db.execute(
        select(schema.Users).filter(schema.Users.company_id == company_id)
    )
    users = result.scalars().all()
    return users

# --- Company Admin: Employee Management ---

@router.get("/pending-employees", response_model=List[schemas.User])
async def get_pending_employees(
    current_admin: Users = Depends(auth.get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session),
    skip: int = 0,
    limit: int = 100
):
    """
    Get a list of users awaiting approval for the admin's company.
    Accessible only by the company's admin.
    """
    pending_employees = await crud.get_pending_employees(
        db, company_id=current_admin.company_id, skip=skip, limit=limit
    )
    return pending_employees


@router.post("/employees/{user_id}/approve", response_model=schemas.User)
async def approve_employee_registration(
    user_id: int,
    current_admin: Users = Depends(auth.get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Approve an employee's registration request.
    Accessible only by the company's admin.
    """
    user_to_approve = await crud.get_user(db, user_id=user_id)

    # Ensure the user exists and belongs to the admin's company
    if not user_to_approve or user_to_approve.company_id != current_admin.company_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your company."
        )

    # Ensure the user is actually pending approval
    if user_to_approve.is_active_in_company:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending approval."
        )

    return await crud.approve_employee(db, user_id=user_id)