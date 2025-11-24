from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.core.dependencies import get_db, get_current_company_admin
from app.models.user_model import Users
from app.models.plan_model import Plan
from app.schemas.subscription_schema import (
    SubscriptionStatus,
    SubscriptionUpgradeRequest,
    PlansWithSubscription,
    TopUpPackageRequest,
    TopUpPackageResponse,
    TopUpPackageOption,
    CustomPlanRequest,
    CustomPlanResponse,
)
from app.modules.subscription.service import subscription_service, TOP_UP_PACKAGES

router = APIRouter()


@router.get("/plans", response_model=PlansWithSubscription)
async def get_available_plans(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Plan).filter(Plan.is_active == True).order_by(Plan.price))
    plans = result.scalars().all()

    current_subscription = None
    try:
        current_subscription = await subscription_service.get_subscription_status(
            db, company_id=current_user.company_id
        )
    except HTTPException as exc:
        # Allow response to succeed when the company has no subscription yet
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise

    top_up_packages = [
        TopUpPackageOption(package_type=key, questions=val["questions"], price=val["price"])
        for key, val in TOP_UP_PACKAGES.items()
    ]

    return PlansWithSubscription(
        plans=plans,
        current_subscription=current_subscription,
        top_up_packages=top_up_packages,
    )


@router.get("/subscriptions/my-status", response_model=SubscriptionStatus)
async def get_my_subscription_status(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    return await subscription_service.get_subscription_status(db, company_id=current_user.company_id)


@router.post("/subscriptions/create-payment")
async def create_payment_for_subscription(
    upgrade_request: SubscriptionUpgradeRequest,
    current_user: Users = Depends(get_current_company_admin),
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


@router.post("/subscriptions/top-up", response_model=TopUpPackageResponse)
async def top_up_subscription(
    topup_request: TopUpPackageRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    return await subscription_service.apply_top_up_package(
        db=db,
        company_id=current_user.company_id,
        package_type=topup_request.package_type,
        user=current_user,
    )


@router.post("/subscriptions/custom-plan", response_model=CustomPlanResponse)
async def request_custom_plan(
    payload: CustomPlanRequest,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    return await subscription_service.submit_custom_plan_request(
        db=db,
        company_id=current_user.company_id,
        user=current_user,
        desired_quota=payload.desired_quota,
        max_users=payload.max_users,
        notes=payload.notes,
    )
