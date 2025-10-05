from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import schemas
from app.services.rag_service import rag_service
from app.services.query_service import query_service
from app.services.gemini_service import gemini_service
from app.utils.auth import get_current_user
from app.utils.helpers import _needs_database_query
from app.database.schema import User, Company
from app.database.connection import db_manager
import uuid

router = APIRouter()

@router.post("/chat", response_model=schemas.ChatResponse, tags=["Chat"])
async def chat_endpoint(
    request: schemas.ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    """
    Main chat endpoint for authenticated and active users. 
    Orchestrates RAG and Dynamic Database queries.
    Requires the user to be active (approved by a company admin).
    """
    if not current_user.is_active:
        raise HTTPException(status_code=403, detail="Your account is not active. Please contact your company admin.")

    try:
        conversation_id = request.conversation_id or str(uuid.uuid4())
        user_message = request.message

        # Get company and division info from the authenticated user
        company_id = current_user.company_id
        division_id = current_user.division_id

        # Step 1: Get relevant context from the company's RAG collection
        rag_context = await rag_service.get_relevant_context(
            query=user_message,
            company_id=company_id
        )
        
        # Step 2: Check if the question seems to require a database query
        needs_database = _needs_database_query(user_message)
        query_results_str = None
        used_database = False
        
        if needs_database:
            # Fetch the company object which contains the db connection string
            company = await db.get(Company, company_id)
            if company:
                # Step 3: Process query using the new DynamicQueryService
                query_result = await query_service.process_user_query(
                    user_query=user_message,
                    company=company,
                    division_id=division_id,
                    db=db # Pass the main app's db session for permission checks
                )
                
                if query_result and query_result.success and query_result.data:
                    query_results_str = query_service.format_query_results(query_result.data)
                    used_database = True
                # Optional: you might want to pass query_result.error to the final prompt

        # Step 4: Generate final response using all available context
        final_response = await gemini_service.generate_chat_response(
            question=user_message,
            context=rag_context,
            query_results=query_results_str,
            company_id=company_id,
            user_role=current_user.role.value,
            db=db
        )
        
        return schemas.ChatResponse(
            reply=final_response,
            conversation_id=conversation_id,
            used_database=used_database
        )
        
    except Exception as e:
        # It's good to log the full error for debugging
        print(f"Unhandled error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Chat error: {str(e)}")


