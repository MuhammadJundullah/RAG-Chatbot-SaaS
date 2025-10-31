from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
from fastapi import HTTPException, status

from app.repository.company_repository import company_repository
from app.schemas import company_schema

async def get_all_active_companies_service(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[company_schema.Company]:
    companies = await company_repository.get_active_companies(db, skip=skip, limit=limit)
    return companies

async def get_pending_companies_service(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[company_schema.Company]:
    companies = await company_repository.get_pending_companies(db, skip=skip, limit=limit)
    return companies

async def approve_company_service(
    db: AsyncSession,
    company_id: int
):
    approval_status = await company_repository.approve_company(db, company_id=company_id)
    
    if approval_status == "approved":
        return {"message": f"Company with id {company_id} has been approved."}
    elif approval_status == "already_active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Company with id {company_id} is already active."
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

async def reject_company_service(
    db: AsyncSession,
    company_id: int
):
    company_to_reject = await company_repository.get_company(db, company_id=company_id)
    if not company_to_reject:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Company with id {company_id} not found."
        )

    if company_to_reject.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot reject an active company."
        )

    await company_repository.reject_company(db, company_id=company_id)
    return {"message": f"Company with id {company_id} has been rejected and deleted."}