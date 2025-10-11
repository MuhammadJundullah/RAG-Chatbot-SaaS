from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import make_url
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app import crud
from app.database import schema
from app.database.connection import db_manager
from app.models import schemas
from app.utils.auth import get_current_company_admin
from app.services.connection_manager import external_connection_manager
from app.services.introspection_service import introspection_service
from app.utils.encryption import decrypt_string

router = APIRouter()

@router.post("/company/database-connection", status_code=status.HTTP_200_OK, tags=["Company Management"])
async def set_database_connection(
    db_url_data: schemas.DBConnectionStringCreate,
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Tests and sets the external database connection string for the admin's company.
    This allows the chatbot to connect to and query the company's private database.
    """
    is_successful, message = await external_connection_manager.test_connection(db_url_data.db_url)
    if not is_successful:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to connect to the database: {message}"
        )

    company = await db.get(schema.Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    await crud.set_db_connection_string(db=db, company=company, db_url=db_url_data.db_url)
    
    return {"status": "success", "message": "Database connection tested and updated successfully."}

@router.get("/company/database-connection", response_model=schemas.DBConnectionStatus, tags=["Company Management"])
async def get_database_connection_status(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Gets the status of the external database connection for the admin's company.
    Returns whether a connection is configured and the database host if available.
    """
    company = await db.get(schema.Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    if not company.encrypted_db_connection_string:
        return schemas.DBConnectionStatus(is_configured=False)

    try:
        decrypted_url = decrypt_string(company.encrypted_db_connection_string)
        url_obj = make_url(decrypted_url)
        host = url_obj.host
    except Exception:
        host = "Could not parse host"

    return schemas.DBConnectionStatus(is_configured=True, db_host=host)

@router.delete("/company/database-connection", status_code=status.HTTP_200_OK, tags=["Company Management"])
async def delete_database_connection(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Deletes the external database connection string for the admin's company.
    This will disable the chatbot's ability to query the company's database.
    """
    company = await db.get(schema.Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    await crud.delete_db_connection_string(db=db, company=company)
    
    return {"status": "success", "message": "Database connection string deleted successfully."}

@router.get("/company/database-schema", tags=["Company Management"])
async def get_external_database_schema(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Introspects the company's external database and returns its schema.
    This helps the company admin understand what data can be queried.
    """
    company = await db.get(schema.Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    schema_data = await introspection_service.get_schema_for_company(company)
    if "error" in schema_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=schema_data["error"])
    
    return schema_data

@router.get("/company/employees", response_model=list[schemas.UserPublic], tags=["Company Employee Management"])
async def get_company_employees(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Gets a list of all employees for the admin's company.
    This allows company admins to view and manage their employees.
    """
    result = await db.execute(
        select(schema.Company)
        .options(selectinload(schema.Company.users))
        .filter(schema.Company.id == current_user.company_id)
    )
    company = result.scalar_one_or_none()

    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    employees = [user for user in company.users if user.role == schema.UserRole.EMPLOYEE]
    return employees

@router.put("/company/employees/{employee_id}/activate", status_code=status.HTTP_200_OK, tags=["Company Employee Management"])
async def activate_employee(
    employee_id: int,
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Activates a pending employee, allowing them to use the chatbot.
    This endpoint is for company admins to approve new employee registrations.
    """
    company = await db.get(schema.Company, current_user.company_id)
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    employee_to_activate = await db.get(schema.User, employee_id)
    if not employee_to_activate or employee_to_activate.company_id != company.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Employee not found in this company.")

    if employee_to_activate.is_active:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Employee is already active.")

    employee_to_activate.is_active = True
    db.add(employee_to_activate)
    await db.commit()

    return {"status": "success", "message": f"Employee {employee_to_activate.username} has been activated."}

@router.get("/company/employees/pending", response_model=list[schemas.UserPublic], tags=["Company Employee Management"])
async def get_pending_employees(
    current_user: schema.User = Depends(get_current_company_admin),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Gets a list of all pending (inactive) employees for the admin's company.
    This helps admins quickly identify and approve new employee registrations.
    """
    result = await db.execute(
        select(schema.Company)
        .options(selectinload(schema.Company.users))
        .filter(schema.Company.id == current_user.company_id)
    )
    company = result.scalar_one_or_none()
    
    if not company:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found.")

    pending_employees = [user for user in company.users if not user.is_active and user.role == schema.UserRole.EMPLOYEE]
    return pending_employees
