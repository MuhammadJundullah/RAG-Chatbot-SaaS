from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List, Optional
from datetime import date
from fastapi import HTTPException
import math
import csv
import io

from app.repository.chatlog_repository import chatlog_repository
from app.repository.conversation_repository import conversation_repository
from app.repository.document_repository import document_repository
from app.repository.user_repository import user_repository
from app.schemas import chatlog_schema, conversation_schema, document_schema
from app.models.user_model import Users
from app.models import chatlog_model
from app.services.gemini_service import gemini_service

"""
This module exposes "_service" helpers for internal use and wrapper functions expected by API routes.
Some routes still import functions like `get_chatlogs` and `get_conversations`, so we provide lightweight
aliases that delegate to the newer helpers to avoid missing-attribute errors.
"""

async def get_all_chatlogs_as_admin_service(
    db: AsyncSession,
    company_id: Optional[int],
    division_id: Optional[int],
    user_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chatlogs = await chatlog_repository.get_all_chatlogs_for_admin(
        db=db,
        company_id=company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs

async def get_chatlogs_as_company_admin_service(
    db: AsyncSession,
    current_user: Users,
    division_id: Optional[int],
    user_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
    skip: int,
    limit: int,
    page: int,
) -> chatlog_schema.PaginatedChatlogResponse:
    chatlogs_data, total_chat = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=current_user.company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    
    total_pages = math.ceil(total_chat / limit) if limit > 0 else 0
    
    return chatlog_schema.PaginatedChatlogResponse(
        chatlogs=[chatlog_schema.ChatlogResponse(**data) for data in chatlogs_data],
        total_pages=total_pages,
        current_page=page,
        total_chat=total_chat,
    )

async def get_conversations_as_company_admin_service(
    db: AsyncSession,
    current_user: Users,
    page: int,
    limit: int,
) -> conversation_schema.PaginatedCompanyConversationResponse:
    skip = (page - 1) * limit
    conversations, total_conversations = await conversation_repository.get_conversations_by_company(
        db=db,
        company_id=current_user.company_id,
        skip=skip,
        limit=limit,
    )
    
    total_pages = math.ceil(total_conversations / limit) if limit > 0 else 0
    
    return conversation_schema.PaginatedCompanyConversationResponse(
        conversations=[conversation_schema.CompanyConversationResponse.from_orm(conv) for conv in conversations],
        total_pages=total_pages,
        current_page=page,
        total_conversations=total_conversations,
    )

async def get_conversation_details_as_company_admin(
    db: AsyncSession,
    current_user: Users,
    conversation_id: str,
) -> conversation_schema.ConversationDetailResponse:
    conversation = await conversation_repository.get_conversation(db, conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    chatlogs = await chatlog_repository.get_chatlogs_by_conversation_id(db, conversation_id)
    if not chatlogs:
        raise HTTPException(status_code=404, detail="No chatlogs found for this conversation")

    user_id = chatlogs[0].UsersId
    chat_user = await user_repository.get_user(db, user_id)
    if not chat_user or chat_user.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this conversation")

    referenced_doc_ids = set()
    for chatlog in chatlogs:
        if chatlog.referenced_document_ids:
            for doc_id in chatlog.referenced_document_ids:
                referenced_doc_ids.add(int(doc_id))

    referenced_documents = [] # Initialize to empty list
    if referenced_doc_ids: # Fetch only if there are IDs
        referenced_documents = await document_repository.get_documents_by_ids(db, list(referenced_doc_ids))

    division_name = chat_user.division if chat_user.division else None

    chat_history = [
        chatlog_schema.ChatMessage(
            question=cl.question,
            answer=cl.answer,
            created_at=cl.created_at
        ) for cl in chatlogs
    ]
    
    referenced_documents_response = [
        document_schema.ReferencedDocument(
            id=doc.id,
            title=doc.title,
            s3_path=doc.s3_path
        ) for doc in referenced_documents
    ]

    return conversation_schema.ConversationDetailResponse(
        conversation_id=conversation.id,
        conversation_title=conversation.title,
        conversation_created_at=conversation.created_at,
        username=chat_user.username,
        division_name=division_name,
        chat_history=chat_history,
        company_id=current_user.company_id,
        referenced_documents=referenced_documents_response,
    )

async def export_chatlogs_as_company_admin_service(
    db: AsyncSession,
    current_user: Users,
    division_id: Optional[int],
    user_id: Optional[int],
    start_date: Optional[date],
    end_date: Optional[date],
) -> str:
    chatlogs_data, _ = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=current_user.company_id,
        division_id=division_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        skip=0,
        limit=-1,
    )

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(["id", "username", "created_at", "question", "answer"])

    for chatlog in chatlogs_data:
        writer.writerow([chatlog["id"], chatlog["username"], chatlog["created_at"], chatlog["question"], chatlog["answer"]])

    return output.getvalue()

async def get_user_chatlogs_service(
    db: AsyncSession,
    current_user: Users,
    start_date: Optional[date],
    end_date: Optional[date],
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chatlogs = await chatlog_repository.get_chatlogs(
        db,
        company_id=current_user.company_id,
        user_id=current_user.id,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )
    return chatlogs

async def get_user_conversation_ids_service(
    db: AsyncSession,
    current_user: Users,
    skip: int,
    limit: int,
) -> List[chatlog_schema.ConversationInfoSchema]:
    """
    Retrieve a list of unique conversations (ID, title, and archived status) for the current user.
    """
    # The repository now returns a list of tuples: (conv_id, title, is_archived)
    conversation_data = await chatlog_repository.get_unique_conversation_ids_for_user(
        db=db,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    # Format the data into ConversationInfoSchema objects
    return [
        chatlog_schema.ConversationInfoSchema(id=str(conv_id), title=title, is_archived=is_archived)
        for conv_id, title, is_archived in conversation_data
    ]

async def get_conversation_history_service(
    db: AsyncSession,
    current_user: Users,
    conversation_id: str,
    skip: int,
    limit: int,
) -> List[chatlog_schema.Chatlog]:
    chat_history_models = await chatlog_repository.get_chat_history(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        skip=skip,
        limit=limit,
    )
    # Convert Chatlog models to Pydantic schemas, ensuring conversation_id is a string
    return [
        chatlog_schema.Chatlog(
            id=chatlog.id,
            question=chatlog.question,
            answer=chatlog.answer,
            UsersId=chatlog.UsersId,
            company_id=chatlog.company_id,
            conversation_id=chatlog.conversation_id,
            created_at=chatlog.created_at
        )
        for chatlog in chat_history_models
    ]

async def delete_conversation_service(
    db: AsyncSession,
    current_user: Users,
    conversation_id: str,
):
    deleted_count = await chatlog_repository.delete_chatlogs_by_conversation_id(
        db=db,
        conversation_id=conversation_id,
        user_id=current_user.id,
    )
    if deleted_count == 0:
        raise HTTPException(status_code=404, detail="Conversation not found or user does not have permission.")
    return {"message": f"Successfully deleted {deleted_count} chatlogs for conversation ID {conversation_id}."}


# ---- Wrapper functions used by existing routers ----

async def get_chatlogs_as_admin(db: AsyncSession, skip: int = 0, limit: int = 100):
    """Backward-compatible wrapper for admin chatlogs endpoint."""
    return await chatlog_repository.get_all_chatlogs_for_admin(
        db=db,
        company_id=None,
        division_id=None,
        user_id=None,
        start_date=None,
        end_date=None,
        skip=skip,
        limit=limit,
    )


async def get_chatlogs_as_company_admin(db: AsyncSession, company_id: int, skip: int = 0, limit: int = 100):
    """Backward-compatible wrapper for company admin chatlogs endpoint."""
    data, _ = await chatlog_repository.get_chatlogs_for_company_admin(
        db=db,
        company_id=company_id,
        division_id=None,
        user_id=None,
        start_date=None,
        end_date=None,
        skip=skip,
        limit=limit,
    )
    return data


async def get_chatlogs(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    """Backward-compatible wrapper for user chatlogs endpoint."""
    return await chatlog_repository.get_chatlogs(
        db=db,
        company_id=None,
        user_id=user_id,
        start_date=None,
        end_date=None,
        skip=skip,
        limit=limit,
    )


async def get_conversations(db: AsyncSession, user_id: int, skip: int = 0, limit: int = 100):
    """Return conversations for a user, matching the router response model."""
    return await conversation_repository.get_conversations_for_user(
        db=db,
        user_id=user_id,
        skip=skip,
        limit=limit,
    )


async def export_chatlogs_as_company_admin(db: AsyncSession, company_id: int, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Wrapper used by the company admin export endpoint."""
    return await export_chatlogs_as_company_admin_service(
        db=db,
        current_user=Users(company_id=company_id),  # Minimal object to satisfy signature
        division_id=None,
        user_id=None,
        start_date=start_date,
        end_date=end_date,
    )


async def export_chatlogs_as_admin(db: AsyncSession, start_date: Optional[date] = None, end_date: Optional[date] = None):
    """Wrapper used by the super admin export endpoint."""
    query = select(
        chatlog_model.Chatlogs.id,
        chatlog_model.Chatlogs.question,
        chatlog_model.Chatlogs.answer,
        chatlog_model.Chatlogs.created_at,
        chatlog_model.Chatlogs.conversation_id,
        Users.username,
    ).join(Users, chatlog_model.Chatlogs.UsersId == Users.id)

    if start_date:
        query = query.filter(chatlog_model.Chatlogs.created_at >= start_date)
    if end_date:
        query = query.filter(chatlog_model.Chatlogs.created_at <= end_date)

    result = await db.execute(query)
    rows = result.all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["id", "username", "created_at", "question", "answer", "conversation_id"])

    for chatlog_id, question, answer, created_at, conversation_id, username in rows:
        writer.writerow([chatlog_id, username, created_at, question, answer, conversation_id])

    return output.getvalue()


async def recommend_topics_for_division_ai(
    db: AsyncSession,
    current_user: Users,
) -> List[str]:
    """Use the LLM to propose 5 short topics for the user's division."""
    division_label = current_user.division or "general"
    prompt = (
        f"Provide 5 short topics (2-3 words each) that an employee in the {division_label} "
        "division should discuss. Respond with topics only, comma-separated, no numbering or extra text. gunakan bahasa indonesia aja"
    )

    response_text = ""
    async for chunk in gemini_service.generate_chat_response(
        question=prompt,
        db=db,
        current_user=current_user,
        context=None,
        query_results=None,
        conversation_history=[],
    ):
        response_text += chunk

    normalized = response_text.replace(";", ",").replace("\n", ",")
    topics = [t.strip(" -•\t") for t in normalized.split(",") if t.strip()]

    if len(topics) < 5:
        fallback = recommend_topics_for_division(current_user.division)
        topics.extend([t for t in fallback if t not in topics])

    return topics[:5]


def recommend_topics_for_division(division: Optional[str]) -> List[str]:
    """Return five short topic suggestions based on division name (static fallback)."""
    default_topics = ["Updates", "Tasks", "Policies", "Onboarding", "FAQ"]
    if not division:
        return default_topics

    division_key = division.strip().lower()
    topic_map = {
        "marketing": ["Campaigns", "Leads", "SEO", "Content", "Budget"],
        "sales": ["Pipeline", "Leads", "Pricing", "Objections", "Quota"],
        "hr": ["Recruitment", "Onboarding", "Policies", "Payroll", "Benefits"],
        "engineering": ["Backlog", "Architecture", "Incidents", "Deployments", "Testing"],
        "it": ["Assets", "Access", "Tickets", "Security", "Maintenance"],
        "finance": ["Budget", "Forecast", "Invoices", "Expenses", "Reporting"],
        "operations": ["SOP", "Vendors", "Logistics", "SLA", "Inventory"],
        "legal": ["Contracts", "Compliance", "Risk", "Policies", "IP"],
        "product": ["Roadmap", "Feedback", "Metrics", "Releases", "Discovery"],
        "support": ["Tickets", "Escalations", "SLA", "Responses", "Knowledge"],
    }
    return topic_map.get(division_key, default_topics)
