
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app import crud
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_user
from app.database.schema import Users

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
    dependencies=[Depends(get_current_user)],
)


@router.get("/pending-users", response_model=List[schemas.User])
async def get_pending_users(
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Get a list of users awaiting approval for the admin's company.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view pending users."
        )
    
    pending_users = await crud.get_pending_users_by_company(db, company_id=current_user.Companyid)
    return pending_users


@router.post("/users/{user_id}/approve", response_model=schemas.User)
async def approve_user(
    user_id: int,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Approve a user's registration.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can approve users."
        )

    user_to_approve = await crud.get_user(db, user_id=user_id)

    if not user_to_approve or user_to_approve.Companyid != current_user.Companyid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your company."
        )

    if user_to_approve.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending approval."
        )

    return await crud.update_user_status(db, user=user_to_approve, status="active")


@router.post("/users/{user_id}/reject")
async def reject_user(
    user_id: int,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Reject and delete a user's registration request.
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reject users."
        )

    user_to_reject = await crud.get_user(db, user_id=user_id)

    if not user_to_reject or user_to_reject.Companyid != current_user.Companyid:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found in your company."
        )

    if user_to_reject.status != "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is not pending approval."
        )

    await crud.delete_user(db, user=user_to_reject)
    return {"status": "success", "message": f"User {user_id} has been rejected and deleted."}
