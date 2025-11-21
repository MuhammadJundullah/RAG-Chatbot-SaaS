from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_active_admin
from app.models.user_model import Users
from app.models.plan_model import Plan
from app.schemas.plan_schema import Plan as PlanSchema
from app.schemas.subscription_schema import SubscriptionStatus, SubscriptionUpgradeRequest
from app.services.subscription_service import subscription_service

router = APIRouter()


@router.get("/plans", response_model=List[PlanSchema])
async def get_available_plans(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Plan).filter(Plan.is_active == True).order_by(Plan.price))
    plans = result.scalars().all()
    return plans


@router.get("/subscriptions/my-status", response_model=SubscriptionStatus)
async def get_my_subscription_status(
    current_user: Users = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    return await subscription_service.get_subscription_status(db, company_id=current_user.company_id)


@router.post("/subscriptions/create-payment")
async def create_payment_for_subscription(
    upgrade_request: SubscriptionUpgradeRequest,
    current_user: Users = Depends(get_current_active_admin),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    return await subscription_service.create_subscription_for_payment(
        db=db,
        company_id=current_user.company_id,
        upgrade_request=upgrade_request,
        user=current_user
    )
