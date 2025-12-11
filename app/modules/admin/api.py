from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, distinct, func
from typing import List, Optional
from math import ceil
import io
from starlette.responses import StreamingResponse
from sqlalchemy.orm import joinedload

from app.core.dependencies import get_current_super_admin, get_db
from app.schemas import company_schema, log_schema, subscription_schema, plan_schema, transaction_schema
from app.modules.admin import service as admin_service
from app.modules.subscription.service import subscription_service
from app.modules.subscription.topup_repository import topup_package_repository
from app.modules.admin.plan_service import plan_service
from app.models.user_model import Users
from app.models.log_model import ActivityLog
from app.models.subscription_model import Subscription
from app.models.plan_model import Plan as PlanModel
from app.models.transaction_model import Transaction
from app.models.company_model import Company

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)

@router.get("/companies", response_model=company_schema.PaginatedCompanyResponse)
async def read_companies(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter status company (active/pending)"),
    search: Optional[str] = Query(None, max_length=100, description="Cari nama, kode, atau email perusahaan"),
):
    skip = (page - 1) * limit
    normalized_search = search.strip() if search and search.strip() else None
    companies = await admin_service.get_companies_service(
        db,
        skip=skip,
        limit=limit,
        status=status,
        page=page,
        search=normalized_search,
    )
    return companies


@router.patch("/companies/{company_id}/approve")
async def approve_company(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await admin_service.approve_company_service(db, company_id=company_id)


@router.patch("/companies/{company_id}/reject")
async def reject_company(
    company_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await admin_service.reject_company_service(db, company_id=company_id)


@router.get("/subscriptions", response_model=List[subscription_schema.Subscription])
async def get_all_subscriptions(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Subscription).options(joinedload(Subscription.plan)))
    subscriptions = result.scalars().all()
    return subscriptions


@router.post("/subscriptions/{subscription_id}/activate-manual", response_model=subscription_schema.Subscription)
async def manual_activate_subscription(
    subscription_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await subscription_service.activate_subscription(db, subscription_id=subscription_id)


@router.post("/companies/{company_id}/add-topup", response_model=subscription_schema.Subscription)
async def add_topup_quota(
    company_id: int,
    topup_data: subscription_schema.SubscriptionTopUpRequest,
    db: AsyncSession = Depends(get_db)
):
    sub = await subscription_service.get_subscription_by_company(db, company_id=company_id)
    sub.top_up_quota += topup_data.quota
    await db.commit()
    await db.refresh(sub, attribute_names=["plan"])
    return sub


@router.post("/plans", response_model=plan_schema.Plan)
async def create_new_plan(
    plan_data: plan_schema.PlanCreate,
    db: AsyncSession = Depends(get_db)
):
    return await plan_service.create_plan(db, plan_data)


@router.get("/plan", response_model=List[plan_schema.Plan])
async def list_all_plans(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(PlanModel).order_by(PlanModel.price))
    plans = result.scalars().all()
    return plans


@router.put("/plans/{plan_id}", response_model=plan_schema.Plan)
async def update_existing_plan(
    plan_id: int,
    plan_data: plan_schema.PlanUpdate,
    db: AsyncSession = Depends(get_db)
):
    return await plan_service.update_plan(db, plan_id, plan_data)


@router.get(
    "/plans-pricing",
    response_model=subscription_schema.AdminPlansPricing,
    summary="Gabungan harga plan & topup (superadmin)"
)
async def get_plans_pricing(
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(PlanModel).order_by(PlanModel.price))
    plans = result.scalars().all()
    topup_packages = await topup_package_repository.list_active(db)
    top_up_options = [
        subscription_schema.TopUpPackageOption(
            package_type=package.package_type,
            questions=package.questions,
            price=package.price,
        )
        for package in topup_packages
    ]
    return subscription_schema.AdminPlansPricing(plans=plans, top_up_packages=top_up_options)


@router.patch(
    "/plans-pricing",
    response_model=subscription_schema.AdminPlansPricing,
    summary="Update harga plan & topup sekaligus (superadmin)"
)
async def update_plans_pricing(
    payload: subscription_schema.PlansPricingUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    if payload.plans:
        await plan_service.bulk_update_prices(db, payload.plans)

    if payload.top_up_packages:
        for package_payload in payload.top_up_packages:
            updated = await topup_package_repository.update_by_type(
                db,
                package_payload.package_type,
                price=package_payload.price,
                questions=package_payload.questions,
                is_active=package_payload.is_active,
            )
            if not updated:
                raise HTTPException(
                    status_code=404,
                    detail=f"Top-up package '{package_payload.package_type}' not found",
                )

    return await get_plans_pricing(db)


@router.delete("/plans/{plan_id}", response_model=plan_schema.Plan)
async def deactivate_existing_plan(
    plan_id: int,
    db: AsyncSession = Depends(get_db)
):
    return await plan_service.deactivate_plan(db, plan_id)


@router.get("/activity-logs", response_model=log_schema.PaginatedActivityLogResponse)
async def get_activity_logs(
    page: int = 1,
    limit: int = 100,
    company_id: Optional[str] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin)
):
    skip_calculated = (page - 1) * limit

    logs, total_count = await admin_service.get_activity_logs_service(
        db=db,
        skip=skip_calculated,
        limit=limit,
        company_id=company_id,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )

    total_pages = ceil(total_count / limit) if limit > 0 else 0

    return log_schema.PaginatedActivityLogResponse(
        logs=logs,
        total_pages=total_pages,
        current_page=page,
        total_logs=total_count
    )


@router.get("/export-logs")
async def export_activity_logs(
    company_id: Optional[str] = None,
    activity_type_category: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin)
):
    csv_data = await admin_service.export_activity_logs_service(
        db=db,
        company_id=company_id,
        activity_type_category=activity_type_category,
        start_date=start_date,
        end_date=end_date
    )

    return StreamingResponse(
        io.StringIO(csv_data),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=activity_logs.csv"}
    )


@router.get(
    "/activity-logs/type",
    response_model=log_schema.CategoryListResponse,
    summary="Dapatkan kategori tipe aktivitas yang unik",
    description="Mengambil daftar nilai unik dari kolom 'activity_type_category' pada log aktivitas."
)
async def get_distinct_activity_categories(
    db: AsyncSession = Depends(get_db),
    company_id: Optional[int] = Query(None, description="Opsional: Filter berdasarkan ID perusahaan"),
):
    try:
        stmt = select(distinct(ActivityLog.activity_type_category))

        if company_id is not None:
            stmt = stmt.where(ActivityLog.company_id == company_id)

        result = await db.execute(stmt)

        distinct_categories = result.scalars().all()

        return log_schema.CategoryListResponse(categories=distinct_categories)

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Terjadi kesalahan saat mengambil kategori distinct: {str(e)}"
        )


@router.get(
    "/transactions",
    response_model=transaction_schema.AdminTransactionListResponse,
    summary="Daftar transaksi (super admin)",
)
async def list_transactions(
    db: AsyncSession = Depends(get_db),
    type: Optional[str] = Query(None, description="Filter berdasarkan type transaksi, contoh: subscription/topup"),
    status: Optional[str] = Query(None, description="Filter status transaksi"),
    company_id: Optional[int] = Query(None, description="Filter company_id"),
    page: int = Query(1, ge=1, description="Nomor halaman"),
    limit: int = Query(100, ge=1, le=500, description="Jumlah data per halaman"),
):
    offset = (page - 1) * limit
    filters = []

    if type:
        filters.append(Transaction.type == type)
    if status:
        filters.append(Transaction.status == status)
    if company_id:
        filters.append(Transaction.company_id == company_id)

    stmt = (
        select(Transaction, Company.name.label("company_name"))
        .join(Company, Transaction.company_id == Company.id)
        .order_by(Transaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    for condition in filters:
        stmt = stmt.where(condition)

    result = await db.execute(stmt)
    rows = result.all()

    items = [
        transaction_schema.AdminTransaction(
            id=tx.id,
            company_name=company_name,
            user_id=tx.user_id,
            type=tx.type,
            plan_id=tx.plan_id,
            package_type=tx.package_type,
            questions_delta=tx.questions_delta,
            amount=tx.amount,
            payment_url=tx.payment_url,
            payment_reference=tx.payment_reference,
            status=tx.status,
            created_at=tx.created_at,
            paid_at=tx.paid_at,
        )
        for tx, company_name in rows
    ]

    count_stmt = select(func.count()).select_from(Transaction).join(Company, Transaction.company_id == Company.id)
    for condition in filters:
        count_stmt = count_stmt.where(condition)
    total_transaction = (await db.execute(count_stmt)).scalar_one()

    total_pages = (total_transaction + limit - 1) // limit if limit > 0 else 0

    return transaction_schema.AdminTransactionListResponse(
        items=items,
        total_transaction=total_transaction,
        current_page=page,
        total_pages=total_pages,
    )
