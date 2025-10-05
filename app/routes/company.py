from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_company_admin

router = APIRouter()

@router.post("/company/database-connection", status_code=status.HTTP_200_OK)
async def set_database_connection(
    db_url_data: schemas.DBConnectionStringCreate,
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Set the external database connection string for the admin's company.
    The connection string will be encrypted before being stored.
    Requires COMPANY_ADMIN authentication.
    """
    # The current_user object from the dependency is not associated with the session
    # that will be used for the update. We need to get the company object from the db.
    company = await db.get(schema.Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    await crud.set_db_connection_string(db=db, company=company, db_url=db_url_data.db_url)
    
    return {"status": "success", "message": "Database connection string updated successfully."}
