from datetime import date, datetime, timedelta
from typing import Dict, List, Optional

from sqlalchemy import func, and_, extract, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user_model import Users
from app.models.company_model import Company
from app.models.subscription_model import Subscription
from app.models.document_model import Documents, DocumentStatus
from app.models.chatlog_model import Chatlogs
from app.models.log_model import ActivityLog


class SuperAdminDashboardService:
    async def get_overview(self, db: AsyncSession) -> dict:
        today = date.today()
        start_of_month = today.replace(day=1)
        start_of_prev_month = (start_of_month - timedelta(days=1)).replace(day=1)
        end_of_prev_month = start_of_month - timedelta(days=1)
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        start_of_prev_week = start_of_week - timedelta(days=7)
        end_of_prev_week = start_of_week - timedelta(days=1)

        # Active company admins
        active_admin_stmt = select(func.count(Users.id)).where(and_(Users.role == "admin", Users.is_active.is_(True)))
        active_company_admins = await db.scalar(active_admin_stmt)

        # Active companies this month (best-effort: active subscription started this month)
        active_companies_stmt = select(func.count(Subscription.id)).where(
            and_(
                Subscription.status == "active",
                Subscription.start_date.isnot(None),
                extract("month", Subscription.start_date) == start_of_month.month,
                extract("year", Subscription.start_date) == start_of_month.year,
            )
        )
        active_companies_this_month = await db.scalar(active_companies_stmt)

        # Total users
        total_users = await db.scalar(select(func.count(Users.id)))
        # WoW change (based on created_at)
        new_users_this_week = await db.scalar(
            select(func.count(Users.id)).where(
                and_(Users.created_at.isnot(None), Users.created_at >= start_of_week)
            )
        )
        new_users_last_week = await db.scalar(
            select(func.count(Users.id)).where(
                and_(
                    Users.created_at.isnot(None),
                    Users.created_at >= start_of_prev_week,
                    Users.created_at <= end_of_prev_week,
                )
            )
        )
        user_wow_change_pct = 0.0
        if new_users_last_week:
            user_wow_change_pct = ((new_users_this_week - new_users_last_week) / new_users_last_week) * 100

        # Documents distribution
        total_documents = await db.scalar(select(func.count(Documents.id)))
        completed_documents = await db.scalar(
            select(func.count(Documents.id)).where(Documents.status == DocumentStatus.COMPLETED)
        )
        failed_documents = await db.scalar(
            select(func.count(Documents.id)).where(
                Documents.status.in_([DocumentStatus.UPLOAD_FAILED, DocumentStatus.PROCESSING_FAILED])
            )
        )
        processing_documents = (total_documents or 0) - (completed_documents or 0) - (failed_documents or 0)

        document_distribution = {
            "total": total_documents or 0,
            "completed": completed_documents or 0,
            "processing": processing_documents,
            "failed": failed_documents or 0,
        }

        # Chats this month and last month
        chats_this_month = await db.scalar(
            select(func.count(Chatlogs.id)).where(Chatlogs.created_at >= start_of_month)
        )
        chats_last_month = await db.scalar(
            select(func.count(Chatlogs.id)).where(
                and_(Chatlogs.created_at >= start_of_prev_month, Chatlogs.created_at <= end_of_prev_month)
            )
        )
        chat_mom_change_pct = 0.0
        if chats_last_month:
            chat_mom_change_pct = ((chats_this_month - chats_last_month) / chats_last_month) * 100

        # Daily chat counts for last 30 days
        start_30d = today - timedelta(days=29)
        daily_counts: Dict[str, int] = {}
        daily_stmt = (
            select(func.date(Chatlogs.created_at).label("chat_date"), func.count(Chatlogs.id).label("chat_count"))
            .where(Chatlogs.created_at >= start_30d)
            .group_by(func.date(Chatlogs.created_at))
            .order_by(func.date(Chatlogs.created_at))
        )
        daily_data = await db.execute(daily_stmt)
        for chat_date, chat_count in daily_data.all():
            daily_counts[str(chat_date)] = chat_count
        # Fill missing days
        current = start_30d
        while current <= today:
            key = current.strftime("%Y-%m-%d")
            daily_counts.setdefault(key, 0)
            current += timedelta(days=1)
        daily_counts = dict(sorted(daily_counts.items()))

        # Total questions this month (same as chats)
        total_questions_this_month = chats_this_month

        # Top 5 user logs
        logs_stmt = (
            select(ActivityLog)
            .order_by(ActivityLog.timestamp.desc())
            .limit(5)
        )
        logs = (await db.execute(logs_stmt)).scalars().all()
        top_logs = [
            {
                "id": log.id,
                "timestamp": log.timestamp,
                "user_id": log.user_id,
                "company_id": log.company_id,
                "activity_type_category": log.activity_type_category,
                "activity_description": log.activity_description,
            }
            for log in logs
        ]

        return {
            "active_company_admins": active_company_admins or 0,
            "active_companies_this_month": active_companies_this_month or 0,
            "total_users": total_users or 0,
            "user_wow_change_pct": user_wow_change_pct,
            "document_distribution": document_distribution,
            "chats_this_month": chats_this_month or 0,
            "chat_mom_change_pct": chat_mom_change_pct,
            "daily_chat_counts": daily_counts,
            "document_status_distribution": {
                "completed": completed_documents or 0,
                "processing": processing_documents or 0,
                "failed": failed_documents or 0,
            },
            "total_questions_this_month": total_questions_this_month or 0,
            "top_user_logs": top_logs,
        }


superadmin_dashboard_service = SuperAdminDashboardService()
