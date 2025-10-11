from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from app.config.settings import settings
from typing import List, Optional, Dict, Any
from pypdf import PdfReader
import io
import uuid

class RAGService:
    def __init__(self):
        """Initializes the Pinecone client and the embedding model using the new v3 syntax."""
        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY must be set.")
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        self.index_name = "company-chatbot"
        self.index = pc.Index(self.index_name)
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        print(f"RAGService initialized with Pinecone (v3 syntax). Index: '{self.index_name}'.")

    def _get_namespace(self, company_id: int) -> str:
        """Creates a Pinecone namespace string for a given company ID."""
        return f"company-{company_id}"

    async def list_documents(self, company_id: int) -> List[str]:
        """
        Lists all unique document filenames from the Pinecone index for a company.
        NOTE: This is a best-effort implementation as Pinecone is not optimized
        for listing all metadata values. It queries a large number of vectors
        to build a list of unique sources.
        """
        try:
            namespace = self._get_namespace(company_id)
            # Query for a large number of vectors to get their metadata
            # We query with a dummy vector, as a vector is required.
            dummy_vector = [0.0] * 384
            response = self.index.query(
                vector=dummy_vector,
                top_k=1000, # Adjust as needed for more documents
                include_metadata=True,
                namespace=namespace
            )
            
            if not response.get('matches'):
                return []
            
            # Extract unique source filenames from metadata
            source_files = {match['metadata']['source'] for match in response['matches'] if 'source' in match['metadata']}
            return sorted(list(source_files))
        except Exception as e:
            print(f"Error listing documents for company {company_id}: {e}")
            return []

    async def delete_document(self, company_id: int, filename: str) -> Dict[str, Any]:
        """Deletes all vectors associated with a specific filename from a company's namespace."""
        try:
            namespace = self._get_namespace(company_id)
            # Using metadata filtering to delete
            self.index.delete(
                filter={"source": {"$eq": filename}},
                namespace=namespace
            )
            return {
                "status": "success",
                "message": f"Document '{filename}' and all its associated vectors have been deleted from the index."
            }
        except Exception as e:
            print(f"Error deleting document '{filename}' for company {company_id}: {e}")
            raise e

    async def get_relevant_context(self, query: str, company_id: int, n_results: int = 5) -> str:
        """Retrieves relevant context from Pinecone using vector similarity search."""
        try:
            namespace = self._get_namespace(company_id)
            query_embedding = self.embedding_model.encode(query).tolist()

            response = self.index.query(
                vector=query_embedding,
                top_k=n_results,
                include_metadata=True,
                namespace=namespace
            )

            if response.get('matches'):
                # We stored the original text in the 'content' metadata field
                context = "\n".join([match['metadata']['content'] for match in response['matches'] if 'content' in match['metadata']])
                return context
            return ""
        except Exception as e:
            print(f"RAG error for company {company_id}: {e}")
            return ""

    async def add_documents(self, documents: List[str], company_id: int, source_filename: str):
        """Embeds document chunks and upserts them into the Pinecone index."""
        try:
            namespace = self._get_namespace(company_id)
            embeddings = self.embedding_model.encode(documents).tolist()
            
            vectors_to_upsert = []
            for doc, emb in zip(documents, embeddings):
                vector_id = str(uuid.uuid4())
                metadata = {
                    'source': source_filename,
                    'content': doc
                }
                vectors_to_upsert.append((vector_id, emb, metadata))

            # Upsert in batches if necessary, though for a single doc this is fine
            self.index.upsert(vectors=vectors_to_upsert, namespace=namespace)
            print(f"Added {len(documents)} document chunks to Pinecone for company {company_id}.")
        except Exception as e:
            print(f"Error adding documents for company {company_id}: {e}")
            raise e

    async def process_and_add_document(self, file_content: bytes, file_name: str, company_id: int) -> Dict[str, Any]:
        """Processes a file, chunks it, and adds it to the Pinecone index."""
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

        await self.add_documents(chunks, company_id, file_name)

        return {
            "status": "success",
            "message": f"Document '{file_name}' processed and added to Pinecone for company {company_id}.",
            "chunks_added": len(chunks)
        }

rag_service = RAGService()