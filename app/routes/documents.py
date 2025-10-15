from fastapi import APIRouter, UploadFile, File, HTTPException, Depends, status
from typing import List
import urllib.parse
import uuid

from app.services.rag_service import rag_service
from app.services.ocr_service import extract_text_from_file # Import the OCR service
from app.utils.auth import get_current_user
from app.database.schema import Users
from app.models import schemas
from app import crud
from sqlalchemy.ext.asyncio import AsyncSession
from app.database.connection import db_manager
from sqlalchemy import select

router = APIRouter(
    prefix="/documents",
    tags=["Documents"],
)

# --- RAG Document Management ---

@router.post(
    "/upload", 
    response_model=schemas.DocumentUploadResponse,
)
async def upload_document_to_rag(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user)
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")

    try:
        file_content = await file.read()
        result = await rag_service.process_and_add_document(
            file_content=file_content, 
            file_name=file.filename,
            company_id=current_user.company_id
        )
        
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process document: {str(e)}")

@router.post(
    "/ocr-extract",
    response_model=schemas.OcrExtractResponse,
    status_code=status.HTTP_200_OK,
)
async def ocr_extract_text(
    file: UploadFile = File(...),
    current_user: Users = Depends(get_current_user) # Ensure user is authenticated
):
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file name provided.")
    
    # Check if the file type is supported for OCR
    if file.content_type not in ["application/pdf", "image/jpeg", "image/png", "image/tiff", "image/bmp", "image/webp"]:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported file type for OCR: {file.content_type}. Only PDF and image files are supported."
        )

    try:
        file_content = await file.read()
        extracted_text = await extract_text_from_file(file_content, file.content_type)
        
        if not extracted_text.strip():
            raise HTTPException(status_code=400, detail="No text could be extracted from the file. Please ensure it contains readable text.")

        # Generate a temporary ID for this OCR extraction
        temp_doc_id = str(uuid.uuid4())
        
        # In a real application, you would store extracted_text and file.filename
        # associated with temp_doc_id in a temporary storage (e.g., Redis, a temp DB table)
        # For this example, we'll just return it.
        
        return schemas.OcrExtractResponse(
            extracted_text=extracted_text,
            temp_doc_id=temp_doc_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to perform OCR: {str(e)}")

@router.post(
    "/ocr-embed",
    response_model=schemas.DocumentUploadResponse,
    status_code=status.HTTP_200_OK,
)
async def ocr_embed_document(
    ocr_embed_request: schemas.OcrEmbedRequest,
    current_user: Users = Depends(get_current_user)
):
    # In a real application, you would retrieve the original file content/metadata
    # using ocr_embed_request.temp_doc_id from your temporary storage.
    # For this example, we'll use the confirmed_text directly.
    
    if not ocr_embed_request.confirmed_text.strip():
        raise HTTPException(status_code=400, detail="Confirmed text cannot be empty.")

    try:
        # The rag_service.process_and_add_document expects file_content (bytes)
        # and file_name. We'll simulate this by encoding the confirmed_text.
        # This might need adjustment based on how rag_service actually processes text-only inputs.
        
        # For now, let's assume rag_service can take a string directly or we convert it to bytes.
        # If rag_service strictly expects file_content, we'd need to store the original file
        # or re-create a dummy file from confirmed_text.
        
        # A more robust solution would involve storing the original file content
        # or a reference to it during the ocr-extract step.
        
        # For demonstration, we'll pass the confirmed_text as bytes.
        # The file_name should ideally come from the original upload, linked by temp_doc_id.
        # Here, we're taking it from the request.
        
        result = await rag_service.process_and_add_document(
            file_content=ocr_embed_request.confirmed_text.encode('utf-8'), # Convert string to bytes
            file_name=ocr_embed_request.original_filename,
            company_id=current_user.company_id,
            is_ocr_processed=True # Add a flag to indicate it's OCR processed
        )
        
        if result["status"] == "failed":
            raise HTTPException(status_code=400, detail=result["message"])
            
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to embed OCR document: {str(e)}")

@router.get(
    "/",
    response_model=List[str],
)
async def list_rag_documents(
    current_user: Users = Depends(get_current_user)
):
    documents = await rag_service.list_documents(company_id=current_user.company_id)
    return documents

@router.delete(
    "/{filename}",
    response_model=schemas.DocumentDeleteResponse,
)
async def delete_rag_document(
    filename: str,
    current_user: Users = Depends(get_current_user),
    db: AsyncSession = Depends(db_manager.get_db_session)
):
    decoded_filename = urllib.parse.unquote(filename)
    
    try:
        # 1. Delete from RAG service (Pinecone)
        rag_result = await rag_service.delete_document(
            company_id=current_user.company_id,
            filename=decoded_filename
        )

        # 2. Delete from relational database
        db_document_result = await db.execute(
            select(schema.Documents).filter(
                schema.Documents.title == decoded_filename,
                schema.Documents.company_id == current_user.company_id
            )
        )
        db_document = db_document_result.scalar_one_or_none()

        if db_document:
            await crud.delete_document(db=db, document=db_document)

        if rag_result["status"] == "not_found" and not db_document:
            raise HTTPException(status_code=404, detail="Document not found in RAG or database.")
        
        return {"status": "success", "message": f"Document '{decoded_filename}' deleted successfully."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")

# --- Database Document CRUD ---



@router.get("/db", response_model=List[schemas.Document])
async def read_documents(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    documents = await crud.get_documents(db, skip=skip, limit=limit)
    company_documents = [doc for doc in documents if doc.company_id == current_user.company_id]
    return company_documents

@router.get("/{document_id}/db", response_model=schemas.Document)
async def read_document(
    document_id: int,
    db: AsyncSession = Depends(db_manager.get_db_session),
    current_user: Users = Depends(get_current_user)
):
    db_document = await crud.get_document(db, document_id=document_id)
    if db_document is None:
        raise HTTPException(status_code=404, detail="Document not found")
    if db_document.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="You do not have permission to access this document.")
    return db_document