from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from app.repository import chatlog_repository
from app.core.dependencies import get_current_user, get_db, get_current_super_admin, get_current_company_admin
from app.schemas import chatlog_schema
from app.models.user_model import Users

# Router for super admin
admin_router = APIRouter(
    prefix="/admin/chatlogs",
    tags=["Admin-Chatlogs"],
    dependencies=[Depends(get_current_super_admin)]
)

# Router for company admin
company_admin_router = APIRouter(
    prefix="/company/chatlogs",
    tags=["Company-Admin-Chatlogs"],
    dependencies=[Depends(get_current_company_admin)]
)

# Router for general users
user_router = APIRouter(
    prefix="/chatlogs",
    tags=["Chatlogs"],
    dependencies=[Depends(get_current_user)]
)

@admin_router.get("/", response_model=List[chatlog_schema.Chatlog])
async def read_all_chatlogs_as_admin(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    company_id: Optional[int] = Query(None),
    division_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Retrieve all chatlogs for super admin with optional filtering.
    """
    chatlogs = await chatlog_repository.get_all_chatlogs_for_admin(
        db=db,
        company_id=company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs

@company_admin_router.get("/", response_model=List[chatlog_schema.Chatlog])
async def read_chatlogs_as_company_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
    skip: int = 0,
    limit: int = 100,
    division_id: Optional[int] = Query(None),
    user_id: Optional[int] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    """
    Retrieve chatlogs for the current company admin, filtered by their company.
    """
    chatlogs = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=current_user.company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs


@user_router.get("/", response_model=List[chatlog_schema.Chatlog])
async def read_user_chatlogs(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
):
    """
    Retrieve chatlogs for the current user, filtered by their company.
    """
    chatlogs = await chatlog_repository.get_chatlogs(
        db,
        company_id=current_user.company_id,
        user_id=current_user.id, # Users should only see their own chatlogs
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs