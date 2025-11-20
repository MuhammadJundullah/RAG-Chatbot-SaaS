# app/tasks/subscription_tasks.py
from datetime import datetime
from sqlalchemy.future import select
from app.core.celery_app import celery_app
from app.core.database import db_manager
from app.models.subscription_model import Subscription

@celery_app.task(name="tasks.check_expired_subscriptions")
def check_expired_subscriptions():
    """
    A periodic task to find and mark subscriptions as 'expired'.
    """
    print("--- Running periodic task: Checking for expired subscriptions ---")
    
    # Since this is a background task, we create a new synchronous session
    db_session_gen = db_manager.get_sync_db_session()
    db = next(db_session_gen)
    
    try:
        expired_subs = db.query(Subscription).filter(
            Subscription.status == 'active',
            Subscription.end_date < datetime.utcnow()
        ).all()

        if not expired_subs:
            print("No expired subscriptions found.")
            return

        for sub in expired_subs:
            print(f"Subscription for company {sub.company_id} has expired. Updating status.")
            sub.status = 'expired'
        
        db.commit()
        print(f"Successfully processed {len(expired_subs)} expired subscriptions.")

    except Exception as e:
        print(f"Error during check_expired_subscriptions task: {e}")
        db.rollback()
    finally:
        db.close()
