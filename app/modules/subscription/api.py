from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.core.dependencies import get_db, get_current_company_admin, get_current_user
from app.models.user_model import Users
from app.models.plan_model import Plan
from app.models.transaction_model import Transaction
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
from app.schemas.transaction_schema import TransactionListResponse
from app.modules.subscription.service import subscription_service, TOP_UP_PACKAGES
from app.schemas.transaction_schema import TransactionReceiptResponse

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
    current_user: Users = Depends(get_current_user),
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
        estimated_employees=payload.estimated_employees,
        need_internal_integration=payload.need_internal_integration,
        special_requests=payload.special_requests,
    )


@router.get(
    "/subscriptions/transactions",
    response_model=TransactionListResponse,
    summary="Daftar transaksi milik company admin",
)
async def list_my_transactions(
    limit: int = 100,
    offset: int = 0,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    base_filter = Transaction.company_id == current_user.company_id
    stmt = (
        select(Transaction)
        .where(base_filter)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    items = result.scalars().all()

    total_stmt = select(func.count()).select_from(Transaction).where(base_filter)
    total = (await db.execute(total_stmt)).scalar_one()

    return TransactionListResponse(items=items, total=total)


@router.get(
    "/subscriptions/transactions/{transaction_id}/receipt",
    response_model=TransactionReceiptResponse,
    summary="Dapatkan bukti pembayaran atau link bayar",
)
async def get_transaction_receipt(
    transaction_id: int,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
):
    tx = await db.get(Transaction, transaction_id)
    if not tx or tx.company_id != current_user.company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaksi tidak ditemukan")

    if tx.status != "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaksi belum dibayar")

    receipt_payload = await subscription_service.fetch_receipt_live(tx) or {}
    if not receipt_payload:
        receipt_payload = {"status": "paid", "reference": tx.payment_reference}

    return TransactionReceiptResponse(
        transaction_id=tx.id,
        status=tx.status,
        payment_url=tx.payment_url,
        receipt=receipt_payload,
    )
