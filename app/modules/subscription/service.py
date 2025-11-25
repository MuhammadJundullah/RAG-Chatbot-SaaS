from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from sqlalchemy import func
from app.models import Subscription, Company, Plan, Users
from app.schemas.subscription_schema import (
    SubscriptionStatus,
    SubscriptionUpgradeRequest,
    TopUpPackageResponse,
    CustomPlanResponse,
)
from app.modules.payment.service import ipaymu_service
from app.utils.email_sender import send_brevo_email
from app.models.transaction_model import Transaction
from app.repository.document_repository import document_repository

TOP_UP_PACKAGES = {
    "large": {"questions": 5000, "price": 50000},
    "small": {"questions": 1000, "price": 200000},
}

class SubscriptionService:
    async def get_subscription_by_company(self, db: AsyncSession, company_id: int) -> Subscription:
        result = await db.execute(
            select(Subscription).options(joinedload(Subscription.plan)).filter(Subscription.company_id == company_id)
        )
        subscription = result.scalars().first()
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found for this company")
        return subscription

    async def get_subscription_status(self, db: AsyncSession, company_id: int) -> SubscriptionStatus:
        sub = await self.get_subscription_by_company(db, company_id)
        plan = await db.get(Plan, sub.plan_id)

        unlimited = plan.question_quota == -1
        total_quota = -1 if unlimited else plan.question_quota + sub.top_up_quota
        remaining_quota = -1 if unlimited else max(total_quota - sub.current_question_usage, 0)

        remaining_percentage = 100.0
        if not unlimited:
            remaining_percentage = (remaining_quota / total_quota * 100) if total_quota > 0 else 0.0

        days_until_renewal = None
        if sub.end_date:
            delta_days = (sub.end_date - datetime.utcnow()).days
            days_until_renewal = max(delta_days, 0)

        document_quota = getattr(plan, "document_quota", -1)
        current_documents = await document_repository.count_documents_by_company(db, company_id)
        docs_unlimited = document_quota == -1
        remaining_documents = -1 if docs_unlimited else max(document_quota - current_documents, 0)
        remaining_docs_percentage = 100.0
        if not docs_unlimited:
            remaining_docs_percentage = (
                (remaining_documents / document_quota * 100) if document_quota > 0 else 0.0
            )

        # Users quota
        max_users = plan.max_users
        user_count_query = select(func.count(Users.id)).where(Users.company_id == company_id)
        current_users = (await db.execute(user_count_query)).scalar_one()
        users_unlimited = max_users == -1
        remaining_users = -1 if users_unlimited else max(max_users - current_users, 0)
        remaining_users_percentage = 100.0
        if not users_unlimited:
            remaining_users_percentage = (
                (remaining_users / max_users * 100) if max_users > 0 else 0.0
            )

        return SubscriptionStatus(
            plan_name=plan.name,
            end_date=sub.end_date,
            monthly_quota=plan.question_quota,
            top_up_quota=sub.top_up_quota,
            total_quota=total_quota,
            remaining_quota=remaining_quota,
            remaining_quota_percentage=remaining_percentage,
            document_quota=document_quota,
            current_documents=current_documents,
            remaining_documents=remaining_documents,
            remaining_documents_percentage=remaining_docs_percentage,
            max_users=max_users,
            current_users=current_users,
            remaining_users=remaining_users,
            remaining_users_percentage=remaining_users_percentage,
            days_until_renewal=days_until_renewal,
        )

    async def create_subscription_for_payment(
        self,
        db: AsyncSession,
        company_id: int,
        upgrade_request: SubscriptionUpgradeRequest,
        user: Users,
    ):
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")

        plan = await db.get(Plan, upgrade_request.plan_id)
        if not plan:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

        result = await db.execute(select(Subscription).filter_by(company_id=company_id))
        subscription = result.scalars().first()

        if not subscription:
            subscription = Subscription(company_id=company_id, plan_id=plan.id)
            db.add(subscription)
        else:
            subscription.plan_id = plan.id
            subscription.status = 'pending_payment'

        transaction = Transaction(
            company_id=company_id,
            user_id=user.id if user else None,
            type="subscription",
            plan_id=plan.id,
            amount=plan.price,
            status="pending_payment",
        )
        db.add(transaction)
        await db.commit()

        await db.refresh(subscription)
        await db.refresh(transaction)

        product_name = f"Subscription - {plan.name}"
        payment_url, trx_id = await ipaymu_service.create_payment_link_for_transaction(
            reference_id=str(transaction.id),
            product_name=product_name,
            price=plan.price,
            user=user,
        )
        transaction.payment_reference = trx_id
        transaction.payment_url = payment_url
        subscription.payment_gateway_reference = trx_id
        await db.commit()

        return {"payment_url": payment_url, "transaction_id": transaction.id}

    async def apply_top_up_package(self, db: AsyncSession, company_id: int, package_type: str, user: Users) -> TopUpPackageResponse:
        if package_type not in TOP_UP_PACKAGES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid top-up package type"
            )

        sub = await self.check_active_subscription(db, company_id)
        package = TOP_UP_PACKAGES[package_type]

        transaction = Transaction(
            company_id=company_id,
            user_id=user.id if user else None,
            type="topup",
            plan_id=sub.plan_id,
            package_type=package_type,
            questions_delta=package["questions"],
            amount=package["price"],
            status="pending_payment",
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        product_name = f"Top-up {package_type.upper()} ({package['questions']} Q)"
        payment_url, trx_id = await ipaymu_service.create_payment_link_for_transaction(
            reference_id=str(transaction.id),
            product_name=product_name,
            price=package["price"],
            user=user,
        )
        transaction.payment_reference = trx_id
        transaction.payment_url = payment_url
        await db.commit()

        return TopUpPackageResponse(
            package_type=package_type,
            questions_added=package["questions"],
            price=package["price"],
            transaction_id=transaction.id,
            payment_url=payment_url,
        )

    async def submit_custom_plan_request(
        self,
        db: AsyncSession,
        company_id: int,
        user: Users,
        estimated_employees: int | None,
        need_internal_integration: str | None,
        special_requests: str | None,
    ) -> CustomPlanResponse:
        transaction = Transaction(
            company_id=company_id,
            user_id=user.id if user else None,
            type="custom_plan",
            amount=0,
            status="pending_review",
            metadata_json=json.dumps(
                {
                    "estimated_employees": estimated_employees,
                    "need_internal_integration": need_internal_integration,
                    "special_requests": special_requests,
                }
            ),
        )
        db.add(transaction)
        await db.commit()
        await db.refresh(transaction)

        return CustomPlanResponse(
            request_id=transaction.id,
            status=transaction.status,
            special_requests=special_requests,
        )

    async def approve_custom_plan_request(
        self,
        db: AsyncSession,
        transaction_id: int,
        price: int,
        product_name: str,
    ) -> dict:
        transaction = await db.get(Transaction, transaction_id)
        if not transaction or transaction.type != "custom_plan":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Custom plan request not found")

        if transaction.status != "pending_review":
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request is not pending review")

        user = await db.get(Users, transaction.user_id) if transaction.user_id else None
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Request does not have a requester user")

        transaction.amount = price
        transaction.status = "pending_payment"
        await db.commit()
        await db.refresh(transaction)

        payment_url, trx_id = await ipaymu_service.create_payment_link_for_transaction(
            reference_id=str(transaction.id),
            product_name=product_name,
            price=price,
            user=user,
        )

        transaction.payment_reference = trx_id
        transaction.payment_url = payment_url
        await db.commit()

        email_subject = "Konfirmasi Permintaan Custom Plan"
        email_body = (
            f"<p>Permintaan custom plan Anda telah disetujui.</p>"
            f"<p>Harga: {price}</p>"
            f"<p>Silakan selesaikan pembayaran melalui tautan berikut: <a href='{payment_url}'>Bayar di sini</a></p>"
        )
        await send_brevo_email(to_email=user.email, subject=email_subject, html_content=email_body)

        return {
            "transaction_id": transaction.id,
            "status": transaction.status,
            "payment_url": payment_url,
        }

    async def activate_subscription(self, db: AsyncSession, subscription_id: int) -> Subscription:
        subscription = await db.get(Subscription, subscription_id)
        if not subscription:
            print(f"ERROR: Could not find subscription with ID {subscription_id} to activate.")
            return None
        
        subscription.status = 'active'
        subscription.start_date = datetime.utcnow()
        subscription.end_date = datetime.utcnow() + timedelta(days=30)
        subscription.current_question_usage = 0
        
        await db.commit()
        await db.refresh(subscription)
        print(f"Subscription {subscription.id} for company {subscription.company_id} has been activated.")
        
        return subscription

    async def check_active_subscription(self, db: AsyncSession, company_id: int) -> Subscription:
        result = await db.execute(
            select(Subscription).options(joinedload(Subscription.plan)).filter_by(company_id=company_id)
        )
        sub = result.scalars().first()
        
        if not sub:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="No subscription found for this company.")
            
        if sub.status != 'active':
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Subscription is not active. Current status: {sub.status}")
        
        if sub.end_date and sub.end_date < datetime.utcnow():
            sub.status = 'expired'
            await db.commit()
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Subscription has expired.")
        
        return sub

    async def check_and_increment_usage(self, db: AsyncSession, company_id: int):
        sub = await self.check_active_subscription(db, company_id)
        plan = sub.plan

        if plan.question_quota == -1:
            return

        total_allowed = plan.question_quota + sub.top_up_quota
        if sub.current_question_usage >= total_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Question quota exceeded for the month.")
        
        sub.current_question_usage += 1
        await db.commit()

    async def fetch_receipt_live(self, transaction: Transaction) -> dict | None:
        """Ambil bukti transaksi langsung dari iPaymu (tanpa cache)."""
        trx_id = transaction.payment_reference or str(transaction.id)
        return await ipaymu_service.fetch_transaction_detail(trx_id)

subscription_service = SubscriptionService()
