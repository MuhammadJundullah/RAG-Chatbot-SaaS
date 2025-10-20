from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.repository import company_repository, user_repository
from app.models import user_model, company_model
from app.core.dependencies import get_current_company_admin, get_db, get_current_user, get_current_super_admin
from app.schemas import user_schema, company_schema
from app.models.user_model import Users

router = APIRouter(
    prefix="/companies",
    tags=["Companies"],
)

# mendapatkan users dari satu company 
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


@router.get("/", response_model=List[company_schema.Company])
async def read_companies(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db),
):
    companies = await company_repository.get_companies(db, skip=skip, limit=limit)
    return companies

@router.get("/pending-employees", response_model=List[user_schema.User])
async def get_pending_employees(
    current_admin: user_model.Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100
):
    """
    Get a list of users awaiting approval for the admin's company.
    Accessible only by the company's admin.
    """
    pending_employees = await user_repository.get_pending_employees(
        db, company_id=current_admin.company_id, skip=skip, limit=limit
    )
    return pending_employees

@router.patch("/employees/{user_id}/approve", response_model=user_schema.User)
async def approve_employee_registration(
    user_id: int,
    current_admin: user_model.Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Approve an employee's registration request.
    Accessible only by the company's admin.
    """
    user_to_approve = await user_repository.get_user(db, user_id=user_id)

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

    return await user_repository.approve_employee(db, user_id=user_id)

@router.get("/{company_id}", response_model=company_schema.Company)
async def read_company(
    company_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user)
):
    db_company = await company_repository.get_company(db, company_id=company_id)
    if db_company is None:
        raise HTTPException(status_code=404, detail="Company not found")
    if db_company.id != current_user.company_id and not current_user.is_super_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to view this company's details")
    return db_company