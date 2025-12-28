from fastapi import APIRouter, Depends, Query, HTTPException, Form, UploadFile, File
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
from app.schemas import user_schema
from app.utils.activity_logger import log_activity

router = APIRouter(
    prefix="/admin",
    tags=["Super Admin"],
    dependencies=[Depends(get_current_super_admin)],
)

@router.get("/companies", response_model=company_schema.PaginatedCompanyUserListResponse)
async def read_companies(
    db: AsyncSession = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number"),
    limit: int = Query(100, ge=1, le=1000, description="Items per page"),
    status: Optional[str] = Query(None, description="Filter status company (active/pending)"),
    search: Optional[str] = Query(
        None,
        max_length=100,
        description="Cari nama/kode/email/alamat/telepon; bisa beberapa kata dipisah spasi atau koma",
    ),
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



@router.post("/companies", response_model=company_schema.CompanyDetailWithAdmins)
async def create_company_by_superadmin(
    name: str = Form(...),
    company_email: str = Form(...),
    admin_name: str = Form(...),
    password: str = Form(...),
    code: Optional[str] = Form(None),
    address: Optional[str] = Form(None),
    pic_phone_number: Optional[str] = Form(None),
    is_active: bool = Form(True),
    company_logo: Optional[UploadFile] = File(None),
    admin_profile_picture: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin),
):
    payload = company_schema.CompanySuperadminCreate(
        name=name,
        company_email=company_email,
        admin_name=admin_name,
        password=password,
        code=code,
        address=address,
        pic_phone_number=pic_phone_number,
        is_active=is_active,
    )
    result = await admin_service.create_company_by_superadmin_service(
        db,
        payload=payload,
        company_logo_file=company_logo,
        admin_profile_picture_file=admin_profile_picture,
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=result.id,
        activity_description=f"Superadmin created company {result.name}.",
    )
    return result


@router.get("/companies/{company_id}", response_model=company_schema.CompanyUserListItem)
async def get_company_detail(
    company_id: int,
    db: AsyncSession = Depends(get_db),
):
    return await admin_service.get_company_detail_with_admins(db, company_id=company_id)



@router.put("/companies/{company_id}", response_model=company_schema.CompanyDetailWithAdmins)
async def update_company_by_superadmin(
    company_id: int,
    company_name: Optional[str] = Form(None),
    company_email: Optional[str] = Form(None),
    company_code: Optional[str] = Form(None),
    company_logo: Optional[UploadFile] = File(None),
    company_is_active: Optional[bool] = Form(None),
    company_address: Optional[str] = Form(None),
    company_pic_phone_number: Optional[str] = Form(None),
    company_created_at: Optional[str] = Form(None),
    admin_name: Optional[str] = Form(None),
    admin_profile_picture: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin),
):
    update_payload = company_schema.CompanySuperadminUpdate(
        name=company_name,
        code=company_code,
        address=company_address,
        company_email=company_email,
        pic_phone_number=company_pic_phone_number,
        is_active=company_is_active,
        admin_name=admin_name,
    )
    result = await admin_service.update_company_by_superadmin_service(
        db=db,
        company_id=company_id,
        payload=update_payload,
        logo_file=company_logo,
        target_admin_id=None,
        admin_profile_picture_file=admin_profile_picture,
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id,
        activity_description=f"Superadmin updated company {company_id}.",
    )
    return result


@router.put("/companies/admins/{user_id}", response_model=user_schema.User)
async def update_company_admin_by_superadmin(
    user_id: int,
    payload: user_schema.AdminSuperadminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin),
):
    admin = await admin_service.update_company_admin_by_superadmin_service(
        db=db,
        admin_id=user_id,
        payload=payload,
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=admin.company_id,
        activity_description=f"Superadmin updated admin {user_id} for company {admin.company_id}.",
    )
    return admin


@router.put("/superadmin/me", response_model=user_schema.User)
async def update_superadmin_profile(
    payload: user_schema.SuperAdminUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin),
):
    superadmin = await admin_service.update_superadmin_profile_service(
        db=db,
        superadmin=current_user,
        payload=payload,
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=None,
        activity_description="Superadmin updated own profile.",
    )
    return superadmin


@router.patch("/companies/{company_id}/status", response_model=company_schema.Company)
async def update_company_status(
    company_id: int,
    payload: company_schema.CompanyStatusUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_super_admin),
):
    company = await admin_service.update_company_status_service(
        db=db,
        company_id=company_id,
        is_active=payload.is_active,
    )
    await log_activity(
        db=db,
        user_id=current_user.id,
        activity_type_category="Data/CRUD",
        company_id=company_id,
        activity_description=f"Superadmin set company {company_id} status to {payload.is_active}.",
    )
    return company


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
            updated_at=package.updated_at,
        )
        for package in topup_packages
    ]
    updated_at_candidates = [
        *(plan.updated_at for plan in plans if getattr(plan, "updated_at", None)),
        *(package.updated_at for package in topup_packages if getattr(package, "updated_at", None)),
    ]
    latest_updated_at = max(updated_at_candidates) if updated_at_candidates else None

    return subscription_schema.AdminPlansPricing(
        plans=plans,
        top_up_packages=top_up_options,
        updated_at=latest_updated_at,
    )


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
