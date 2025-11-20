# app/services/subscription_service.py
from datetime import datetime, timedelta
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from sqlalchemy.future import select
from app.models import Subscription, Company, Plan, Users
from app.schemas.subscription_schema import SubscriptionStatus, SubscriptionUpgradeRequest
from app.services.ipaymu_service import ipaymu_service

class SubscriptionService:
    async def get_subscription_by_company(self, db: AsyncSession, company_id: str) -> Subscription:
        result = await db.execute(
            select(Subscription).filter(Subscription.company_id == company_id)
        )
        subscription = result.scalars().first()
        if not subscription:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subscription not found for this company")
        return subscription

    async def get_subscription_status(self, db: AsyncSession, company_id: str) -> SubscriptionStatus:
        sub = await self.get_subscription_by_company(db, company_id)
        plan = await db.get(Plan, sub.plan_id)
        
        total_quota = plan.question_quota + sub.top_up_quota
        remaining = total_quota - sub.current_question_usage
        
        return SubscriptionStatus(
            plan_name=plan.name,
            status=sub.status,
            start_date=sub.start_date,
            end_date=sub.end_date,
            question_quota=plan.question_quota,
            questions_used=sub.current_question_usage,
            top_up_quota=sub.top_up_quota,
            remaining_questions=remaining if plan.question_quota != -1 else -1, # -1 for unlimited
            max_users=plan.max_users
        )

    async def create_subscription_for_payment(self, db: AsyncSession, company_id: str, upgrade_request: SubscriptionUpgradeRequest, user: Users):
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
        
        await db.commit()
        await db.refresh(subscription)

        payment_url, trx_id = await ipaymu_service.create_payment_link(subscription, user)
        
        subscription.payment_gateway_reference = trx_id
        await db.commit()

        return {"payment_url": payment_url}

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

    async def check_active_subscription(self, db: AsyncSession, company_id: str) -> Subscription:
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

    async def check_and_increment_usage(self, db: AsyncSession, company_id: str):
        sub = await self.check_active_subscription(db, company_id)
        plan = sub.plan

        if plan.question_quota == -1:
            return

        total_allowed = plan.question_quota + sub.top_up_quota
        if sub.current_question_usage >= total_allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Question quota exceeded for the month.")
        
        sub.current_question_usage += 1
        await db.commit()

subscription_service = SubscriptionService()
