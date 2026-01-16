from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional
from datetime import date
from fastapi.responses import StreamingResponse
import io

from app.core.dependencies import get_current_user, get_db, get_current_super_admin, get_current_company_admin, get_current_employee
from app.schemas import chatlog_schema, conversation_schema
from app.models.user_model import Users
from app.modules.chatlogs import service as chatlog_service
from app.models.log_model import ActivityLog

admin_router = APIRouter(
    prefix="/admin/chatlogs",
    tags=["Admin-Chatlogs"],
    dependencies=[Depends(get_current_super_admin)]
)

company_admin_router = APIRouter(
    prefix="/company/chatlogs",
    tags=["Company-Admin-Chatlogs"],
    dependencies=[Depends(get_current_company_admin)]
)

user_router = APIRouter(
    prefix="/chatlogs",
    tags=["Chatlogs"],
    dependencies=[Depends(get_current_user)]
)


@admin_router.get("/", response_model=List[chatlog_schema.Chatlog])
async def read_all_chatlogs_as_admin(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    return await chatlog_service.get_chatlogs_as_admin(db, skip=skip, limit=limit)


@company_admin_router.get("/", response_model=chatlog_schema.PaginatedChatlogResponse)
async def read_chatlogs_as_company_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
    page: int = 1,
    limit: int = 100,
    search: Optional[str] = Query(
        None,
        max_length=100,
        description="Cari di pertanyaan, jawaban, username, atau conversation ID"
    ),
):
    """
    Paginated chatlogs for the company admin view.
    """
    skip = (page - 1) * limit
    normalized_search = search.strip() if search and search.strip() else None
    return await chatlog_service.get_chatlogs_as_company_admin_service(
        db=db,
        current_user=current_user,
        division_id=None,
        user_id=None,
        start_date=None,
        end_date=None,
        skip=skip,
        limit=limit,
        page=page,
        search=normalized_search,
    )

@company_admin_router.get("/export")
async def export_chatlogs_as_company_admin(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
    start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format"),
):
    json_data = await chatlog_service.export_chatlogs_as_company_admin(
        db, current_user.company_id, start_date=start_date, end_date=end_date
    )
    json_bytes = json_data.encode('utf-8')
    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=chatlogs.json"}
    )

@company_admin_router.get("/{conversation_id}", response_model=conversation_schema.ConversationDetailResponse)
async def get_conversation_details_as_company_admin(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
):
    """
    Retrieve details for a specific conversation, including chat history and referenced documents.
    """
    conversation_details = await chatlog_service.get_conversation_details_as_company_admin(
        db=db,
        current_user=current_user,
        conversation_id=conversation_id,
    )
    return {**conversation_details.model_dump(), "company_id": current_user.company_id}


@company_admin_router.delete("/{chatlog_id}")
async def delete_chatlog_as_company_admin(
    chatlog_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_company_admin),
):
    """
    Delete a single chatlog entry for the current company.
    """
    return await chatlog_service.delete_chatlog_as_company_admin_service(
        db=db,
        current_user=current_user,
        chatlog_id=chatlog_id,
    )


@user_router.get("/", response_model=List[chatlog_schema.Chatlog])
async def read_chatlogs(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    return await chatlog_service.get_chatlogs(db, user_id=current_user.id, skip=skip, limit=limit)


@user_router.get("/conversations", response_model=conversation_schema.PaginatedConversationResponse)
async def get_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    search: Optional[str] = Query(
        None,
        max_length=100,
        description="Cari di judul percakapan atau isi chat"
    ),
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
):
    normalized_search = search.strip() if search and search.strip() else None
    return await chatlog_service.get_conversations(
        db,
        user_id=current_user.id,
        page=page,
        limit=limit,
        search=normalized_search,
    )


@user_router.get("/{conversation_id}", response_model=List[chatlog_schema.Chatlog])
async def get_conversation_history(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
    skip: int = 0,
    limit: int = 100,
):
    """
    Retrieve chat history for a conversation the user participates in.
    """
    return await chatlog_service.get_conversation_history_service(
        db=db,
        current_user=current_user,
        conversation_id=conversation_id,
        skip=skip,
        limit=limit,
    )


@user_router.delete("/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_user),
):
    """
    Delete all chatlogs for a conversation owned by the current user.
    """
    return await chatlog_service.delete_conversation_service(
        db=db,
        current_user=current_user,
        conversation_id=conversation_id,
    )


@user_router.get("/recommendations/topics", response_model=chatlog_schema.TopicRecommendations)
async def recommend_topics_for_employee(
    db: AsyncSession = Depends(get_db),
    current_user: Users = Depends(get_current_employee),
):
    """
    Provide five short topic suggestions based on the employee's division.
    """
    topics = await chatlog_service.recommend_topics_for_division_ai(db=db, current_user=current_user)
    return {"topics": topics}


@admin_router.get("/export")
async def export_chatlogs_as_admin(
    db: AsyncSession = Depends(get_db),
    start_date: Optional[date] = Query(None, description="Start date in YYYY-MM-DD format"),
    end_date: Optional[date] = Query(None, description="End date in YYYY-MM-DD format"),
):
    json_data = await chatlog_service.export_chatlogs_as_admin(
        db, start_date=start_date, end_date=end_date
    )
    json_bytes = json_data.encode('utf-8')
    return StreamingResponse(
        io.BytesIO(json_bytes),
        media_type="application/json",
        headers={"Content-Disposition": "attachment; filename=chatlogs.json"}
    )
