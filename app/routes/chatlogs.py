from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date

from app import crud
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_user
from app.database.schema import Users

router = APIRouter(
    prefix="/chatlogs",
    tags=["Chatlogs"],
)

@router.get("/", response_model=List[schemas.Chatlog])
async def read_chatlogs(
    company_id: Optional[int] = None,
    user_id: Optional[int] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user),
):
    # In a real application, you'd want to add authorization here
    # to ensure only admins can see all logs.
    # For now, we'll just filter by the user's company.
    if company_id and company_id != current_user.Companyid:
        # If a company_id is provided, it must match the user's company
        # Or the user must be a super-admin, which we are not implementing now.
        company_id = current_user.Companyid
        
    if not company_id:
        company_id = current_user.Companyid

    chatlogs = await crud.get_chatlogs(
        db,
        company_id=company_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs
