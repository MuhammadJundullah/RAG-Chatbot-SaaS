from fastapi import APIRouter, Depends, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.dependencies import get_current_user, get_db, get_current_company_admin
from app.models.user_model import Users
from app.schemas import company_schema, user_schema # Import user_schema
from app.services import company_service

router = APIRouter(
    prefix="/company",
    tags=["Company"],
)

# --- NEW ENDPOINT FOR UPDATING COMPANY DETAILS ---
@router.put("/update", response_model=company_schema.Company)
async def update_my_company(
    name: str = Form(...),
    code: str = Form(...),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Updates the company's name and code.
    Requires the user to be a company administrator.
    """
    # The 'db' and 'current_user' parameters are correctly injected by FastAPI's dependency injection system.
    # They are available for use within this function.
    return await company_service.update_my_company_service(
        db=db,
        current_user=current_user,
        name=name,
        code=code,
    )

# --- Existing endpoints (assuming they are correct and not modified here) ---

@router.get("/", response_model=company_schema.Company)
async def read_my_company(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user) # Changed to get_current_user for broader access
):
    """
    Gets the current user's company details.
    Accessible by any logged-in user.
    """
    return await company_service.read_my_company_service(
        db=db,
        current_user=current_user
    )

@router.get("/users", response_model=List[user_schema.User]) # Changed response_model to List[user_schema.User]
async def get_company_users_endpoint(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin)
):
    """
    Gets a list of all users within the company.
    Accessible only by company administrators.
    """
    return await company_service.get_company_users_service(
        db=db,
        current_user=current_user
    )

@router.get("/active", response_model=List[company_schema.Company])
async def get_active_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Gets a list of active companies, supporting pagination."""
    skip_calculated = (page - 1) * limit
    return await company_service.get_active_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )

@router.get("/pending-approval", response_model=List[company_schema.Company])
async def get_pending_approval_companies(
    page: int = 1,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Gets a list of companies that are pending approval."""
    skip_calculated = (page - 1) * limit
    return await company_service.get_pending_approval_companies_service(
        db=db,
        skip=skip_calculated,
        limit=limit
    )
