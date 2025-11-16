from sqlalchemy.ext.asyncio import AsyncSession
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