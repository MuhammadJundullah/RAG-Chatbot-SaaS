from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sse_starlette.sse import EventSourceResponse
import json

from app.models import schemas
from app.services.rag_service import rag_service
from app.services.query_service import query_service
from app.services.gemini_service import gemini_service
from app.services.introspection_service import introspection_service
from app.utils.auth import get_current_user
from app.database.schema import User, Company
from app.database.connection import db_manager
import uuid

router = APIRouter()

@router.post("/chat", tags=["Chat"])
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

    async def event_generator():
        try:
            conversation_id = request.conversation_id or str(uuid.uuid4())
            user_message = request.message

            company_id = current_user.company_id
            division_id = current_user.division_id

            rag_context = await rag_service.get_relevant_context(
                query=user_message,
                company_id=company_id
            )
            
            company = await db.get(Company, company_id)
            needs_database = False
            if company and company.encrypted_db_connection_string:
                schema_data = await introspection_service.get_schema_for_company(company)
                if not schema_data.get("error"):
                    full_schema_str = ""
                    for table in schema_data.get("schema", []):
                        full_schema_str += f"- Table: {table['table_name']}\n"
                        for column in table['columns']:
                            full_schema_str += f"  - Column: {column}\n"
                    
                    needs_database = await gemini_service.should_query_database(user_message, full_schema_str)

            query_results_str = None
            used_database = False
            
            if needs_database:
                if company:
                    query_result = await query_service.process_user_query(
                        user_query=user_message,
                        company=company,
                        division_id=division_id,
                        db=db
                    )
                    
                    if query_result and query_result.success and query_result.data:
                        query_results_str = query_service.format_query_results(query_result.data)
                        used_database = True
                    elif query_result and query_result.error:
                         query_results_str = f"Database query failed with error: {query_result.error}"


            async for chunk in gemini_service.generate_chat_response(
                question=user_message,
                context=rag_context,
                query_results=query_results_str,
                company_id=company_id,
                user_role=current_user.role.value,
                db=db
            ):
                yield {"event": "message", "data": chunk}
            
            # Send a final event with metadata
            yield {
                "event": "end",
                "data": json.dumps({
                    "conversation_id": conversation_id,
                    "used_database": used_database
                })
            }
            
        except Exception as e:
            print(f"Unhandled error in chat endpoint: {e}")
            yield {"event": "error", "data": json.dumps({"detail": f"Chat error: {str(e)}", "status_code": 500})}

    return EventSourceResponse(event_generator())
