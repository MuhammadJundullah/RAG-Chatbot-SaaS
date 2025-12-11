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
)
from app.schemas.plan_schema import PlanPublic
from app.schemas.transaction_schema import TransactionListResponse
from app.modules.subscription.service import subscription_service
from app.modules.subscription.topup_repository import topup_package_repository
from app.schemas.transaction_schema import TransactionReceiptResponse, PaymentSuccessResponse

router = APIRouter()


async def _get_transaction_product_name(tx: Transaction, db: AsyncSession) -> str:
    """Resolve a user-friendly product name for subscription vs top-up."""
    if tx.type == "subscription":
        plan = await db.get(Plan, tx.plan_id) if tx.plan_id else None
        return plan.name if plan else "Subscription Plan"
    if tx.type == "topup":
        package = await topup_package_repository.get_by_type(db, tx.package_type or "")
        if package:
            return f"Top-up {package.package_type.upper()} ({package.questions} Q)"
        return f"Top-up {tx.package_type or ''}".strip()
    return "Transaction"


async def _get_subscription_period_and_status_by_company(db: AsyncSession, company_id: int):
    """Fetch subscription for a company and return period/status safely."""
    subscription = await subscription_service.get_subscription_by_company_optional(db, company_id=company_id)
    if not subscription:
        return None, None, None
    return subscription.start_date, subscription.end_date, subscription.status


@router.get("/plans", response_model=PlansWithSubscription)
async def get_available_plans(
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Plan).filter(Plan.is_active == True).order_by(Plan.price))
    plans = result.scalars().all()

    def format_quota(value: int | None, label: str) -> str:
        return "Tanpa batas" if value is None or value == -1 else f"{value} {label}"

    def format_bool(flag: bool, true_label: str, false_label: str) -> str:
        return true_label if flag else false_label

    def format_price(amount: int) -> str:
        return f"Rp {amount:,.0f}".replace(",", ".")

    formatted_plans = [
        PlanPublic(
            id=plan.id,
            name=plan.name,
            price=format_price(plan.price),
            question_quota=format_quota(plan.question_quota, "pertanyaan / bulan"),
            max_users=format_quota(plan.max_users, "user"),
            document_quota=format_quota(getattr(plan, "document_quota", -1), "dokumen"),
            recomended_for=plan.recomended_for or "",
            allow_custom_prompts=format_bool(
                plan.allow_custom_prompts,
                "Ada Custom Prompt",
                "Tidak ada Custom Prompt",
            ),
            api_access=format_bool(plan.api_access, "Akses API SmartAI", "Tidak ada akses API SmartAI"),
            is_active=format_bool(plan.is_active, "Aktif", "Tidak aktif"),
        )
        for plan in plans
    ]

    current_subscription = None
    try:
        current_subscription = await subscription_service.get_subscription_status(
            db, company_id=current_user.company_id
        )
    except HTTPException as exc:
        # Allow response to succeed when the company has no subscription yet
        if exc.status_code != status.HTTP_404_NOT_FOUND:
            raise

    top_up_packages_db = await subscription_service.list_active_topup_packages(db)
    top_up_packages = [
        TopUpPackageOption(package_type=p.package_type, questions=p.questions, price=p.price)
        for p in top_up_packages_db
    ]

    return PlansWithSubscription(
        plans=formatted_plans,
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

    if upgrade_request.transaction_type == "topup":
        return await subscription_service.create_topup_payment(
            db=db,
            company_id=current_user.company_id,
            package_type=upgrade_request.package_type,
            user=current_user,
            success_return_url=upgrade_request.success_return_url,
            failed_return_url=upgrade_request.failed_return_url,
        )

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


@router.get(
    "/subscriptions/transactions",
    response_model=TransactionListResponse,
    summary="Daftar transaksi milik company admin",
)
async def list_my_transactions(
    page: int = 1,
    limit: int = 100,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
):
    if not current_user.company_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="User is not associated with a company")

    page = max(page, 1)
    limit = max(limit, 1)
    offset = (page - 1) * limit

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

    total_pages = (total + limit - 1) // limit if limit > 0 else 0

    return TransactionListResponse(
        items=items,
        total=total,
        current_page=page,
        total_pages=total_pages,
    )


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
    plan_name = await _get_transaction_product_name(tx, db)

    return TransactionReceiptResponse(
        transaction_id=tx.id,
        status=tx.status,
        payment_url=tx.payment_url,
        plan_name=plan_name,
        receipt=receipt_payload,
    )

@router.get(
    "/subscriptions/transactions/receipt",
    response_model=TransactionReceiptResponse,
    summary="Dapatkan bukti pembayaran berdasarkan trx_id (payment_reference) atau id transaksi",
)
async def get_transaction_receipt_by_reference(
    trx_id: str | None = None,
    transaction_id: int | None = None,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
):
    if not trx_id and not transaction_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="trx_id atau transaction_id harus diisi",
        )

    tx = None
    if trx_id:
        stmt = select(Transaction).where(
            Transaction.payment_reference == trx_id,
            Transaction.company_id == current_user.company_id,
        )
        result = await db.execute(stmt)
        tx = result.scalars().first()

    if not tx and transaction_id:
        tx = await db.get(Transaction, transaction_id)
        if tx and tx.company_id != current_user.company_id:
            tx = None

    if not tx and trx_id and trx_id.isdigit():
        fallback_stmt = select(Transaction).where(
            Transaction.id == int(trx_id),
            Transaction.company_id == current_user.company_id,
        )
        fallback_result = await db.execute(fallback_stmt)
        tx = fallback_result.scalars().first()

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaksi tidak ditemukan")

    if tx.status != "paid":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transaksi belum dibayar")

    receipt_payload = await subscription_service.fetch_receipt_live(tx) or {}
    if not receipt_payload:
        receipt_payload = {"status": "paid", "reference": tx.payment_reference}
    plan_name = await _get_transaction_product_name(tx, db)

    return TransactionReceiptResponse(
        transaction_id=tx.id,
        status=tx.status,
        payment_url=tx.payment_url,
        receipt=receipt_payload,
        plan_name=plan_name,
    )


@router.get(
    "/subscriptions/transactions/payment-success",
    response_model=PaymentSuccessResponse,
    summary="Halaman sukses pembayaran berdasarkan trx_id",
)
async def get_payment_success_info(
    trx_id: str | None = None,
    current_user: Users = Depends(get_current_company_admin),
    db: AsyncSession = Depends(get_db),
):
    if not trx_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="trx_id harus diisi",
        )

    stmt = select(Transaction).where(
        Transaction.payment_reference == trx_id,
        Transaction.company_id == current_user.company_id,
    )
    result = await db.execute(stmt)
    tx = result.scalars().first()

    if not tx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Transaksi tidak ditemukan")

    plan_name = await _get_transaction_product_name(tx, db)
    active_start, active_end, subscription_status = await _get_subscription_period_and_status_by_company(
        db, current_user.company_id
    )

    return PaymentSuccessResponse(
        transaction_id=tx.id,
        transaction_type=tx.type,
        transaction_status=tx.status,
        plan_name=plan_name,
        active_start=active_start,
        active_end=active_end,
        subscription_status=subscription_status,
    )
