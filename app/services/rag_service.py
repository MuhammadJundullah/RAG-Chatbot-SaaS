import chromadb
import onnxruntime
import chromadb.utils.embedding_functions as embedding_functions
from app.config.settings import settings
from typing import List, Optional, Dict, Any
from pypdf import PdfReader
import io
import uuid

# Force ONNX runtime to use CPU only, to avoid CoreML bugs on macOS.
# This is an aggressive approach to ensure it takes effect before ChromaDB initializes it.
try:
    if 'CoreMLExecutionProvider' in onnxruntime.get_available_providers():
        onnxruntime.set_available_providers(['CPUExecutionProvider'])
        print("ONNX runtime provider forced to CPU.")
except Exception as e:
    print(f"Could not set ONNX provider: {e}")


class RAGService:
    def __init__(self):
        self.client = chromadb.PersistentClient(path=settings.VECTOR_DB_PATH)
        self.embedding_function = embedding_functions.DefaultEmbeddingFunction()

    def _get_collection_for_company(self, company_id: int):
        """Gets or creates a ChromaDB collection for a specific company."""
        collection_name = f"company_{company_id}"
        return self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )

    async def list_documents(self, company_id: int) -> List[str]:
        """
        Lists all unique document filenames present in a company's collection.
        """
        collection = self._get_collection_for_company(company_id)
        try:
            results = collection.get()
            
            if not results or not results.get('metadatas'):
                return []
            
            source_files = {
                metadata['source'] 
                for metadata in results['metadatas'] 
                if metadata and 'source' in metadata
            }
            return sorted(list(source_files))
        except Exception as e:
            print(f"Error listing documents for company {company_id}: {e}")
            return []

    async def delete_document(self, company_id: int, filename: str) -> Dict[str, Any]:
        """
        Deletes all chunks associated with a specific filename from a company's collection.
        """
        collection = self._get_collection_for_company(company_id)
        try:
            existing_chunks = collection.get(where={"source": filename}, include=[])
            num_to_delete = len(existing_chunks.get('ids', []))

            if num_to_delete == 0:
                 return {"status": "not_found", "message": f"No document found with filename '{filename}'."}

            collection.delete(where={"source": filename})
            
            return {
                "status": "success", 
                "message": f"Document '{filename}' and all its associated chunks have been deleted.",
                "chunks_deleted": num_to_delete
            }
        except Exception as e:
            print(f"Error deleting document '{filename}' for company {company_id}: {e}")
            raise e

    async def get_relevant_context(self, query: str, company_id: int, n_results: int = 3) -> str:
        """
        Retrieve relevant context from a company's specific vector database collection.
        """
        collection = self._get_collection_for_company(company_id)
        try:
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )

            if results['documents'] and results['documents'][0]:
                context = "\n".join(results['documents'][0])
                return context
            return ""
        except Exception as e:
            print(f"RAG error for company {company_id}: {e}")
            return ""

    async def add_documents(self, documents: List[str], company_id: int, metadata: Optional[List[dict]] = None):
        """
        Add documents to a company's specific vector database collection.
        """
        collection = self._get_collection_for_company(company_id)
        try:
            ids = [str(uuid.uuid4()) for _ in documents]

            collection.add(
                documents=documents,
                metadatas=metadata if metadata else [{}] * len(documents),
                ids=ids
            )
            print(f"Added {len(documents)} document chunks to ChromaDB for company {company_id}.")
        except Exception as e:
            # Re-raise the exception so the error is not silent
            print(f"Error adding documents for company {company_id}: {e}")
            raise e

    async def process_and_add_document(self, file_content: bytes, file_name: str, company_id: int) -> Dict[str, Any]:
        """
        Processes a document, extracts text, chunks it, and adds it to the
        company's specific ChromaDB collection.
        """
        text_content = ""
        if file_name.lower().endswith(".pdf"):
            try:
                reader = PdfReader(io.BytesIO(file_content))
                for page in reader.pages:
                    text_content += page.extract_text() + "\n"
            except Exception as e:
                raise ValueError(f"Failed to extract text from PDF: {e}")
        else:
            try:
                text_content = file_content.decode('utf-8')
            except UnicodeDecodeError:
                raise ValueError("Unsupported file type or encoding for non-PDF file.")

        if not text_content.strip():
            return {"status": "failed", "message": "No extractable text found in document."}

        chunk_size = 1000
        overlap = 200
        chunks = [
            text_content[i:i + chunk_size]
            for i in range(0, len(text_content), chunk_size - overlap)
        ]

        if not chunks:
            return {"status": "failed", "message": "Could not chunk document text."}

        metadatas = [{"source": file_name, "chunk_index": i} for i in range(len(chunks))]

        await self.add_documents(chunks, company_id, metadatas)

        return {
            "status": "success",
            "message": f"Document '{file_name}' processed and added to ChromaDB for company {company_id}.",
            "chunks_added": len(chunks)
        }

rag_service = RAGService()