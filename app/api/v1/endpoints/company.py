from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.repository import company_repository, division_repository
from app.models import user_model
from app.core.dependencies import get_current_company_admin, get_db
from app.schemas import user_schema, company_schema
from app.services import user_service

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

# get all users of company
@router.get("/", response_model=List[company_schema.Company])
async def read_companies(
    skip: int = 0, limit: int = 100, db: AsyncSession = Depends(get_db),
):
    companies = await company_repository.get_active_companies(db, skip=skip, limit=limit)
    return companies

# 
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