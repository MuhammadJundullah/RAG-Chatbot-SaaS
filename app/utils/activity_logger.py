import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.log_model import ActivityLog # Import the model

async def log_activity(
    db: AsyncSession,
    user_id: Optional[int], # Changed to Integer to match Users.id
    activity_type_category: str,
    company_id: Optional[int], # Changed to Integer to match Company.id
    activity_description: str,
    timestamp: Optional[datetime.datetime] = None
):
    """
    Logs user activity to the database.

    Args:
        db: The database session.
        user_id: The ID of the user performing the activity.
        activity_type_category: The broad category of the activity (e.g., "Login/Akses", "Data/CRUD").
        company_id: The ID of the company associated with the user or activity.
        activity_description: A human-readable description of what happened.
        timestamp: The datetime of the activity. Defaults to now.
    """
    if timestamp is None:
        timestamp = datetime.datetime.utcnow()

    log_entry = ActivityLog(
        timestamp=timestamp,
        user_id=user_id,
        activity_type_category=activity_type_category,
        company_id=company_id,
        activity_description=activity_description
    )
    
    db.add(log_entry)
    await db.commit()
    # Optionally, you can still print for debugging if needed
    # print(f"Logged activity: {log_entry.activity_description}")

