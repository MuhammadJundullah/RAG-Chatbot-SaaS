from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
from app.core.config import settings
from typing import List, Dict, Any, Optional
import uuid
import asyncio

class RAGService:
    def __init__(self):

        if not settings.PINECONE_API_KEY:
            raise ValueError("PINECONE_API_KEY must be set.")
        
        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        
        self.index_name = "smartai"
        self.index = pc.Index(self.index_name)
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL_NAME)
        print(f"RAGService initialized. Index: '{self.index_name}'.")

    def _get_namespace(self, company_id: int) -> str:
        return f"company-{company_id}"

    async def delete_document(self, company_id: int, filename: str) -> Dict[str, Any]:
        namespace = self._get_namespace(company_id)
        try:
            await asyncio.to_thread(self.index.delete, filter={"source": {"$eq": filename}}, namespace=namespace)
            return {"status": "success"}
        except Exception as e:
            if "Namespace not found" in str(e):
                return {"status": "success", "message": "Document not in vector index."}
            else:
                raise e

    async def delete_document_by_id(self, document_id: str, company_id: int) -> Dict[str, Any]:
        namespace = self._get_namespace(company_id)
        try:
            await asyncio.to_thread(self.index.delete, filter={"document_id": {"$eq": document_id}}, namespace=namespace)
            return {"status": "success"}
        except Exception as e:
            if "Namespace not found" in str(e):
                return {"status": "success", "message": "Document not in vector index."}
            else:
                raise e

    async def update_document_content(self, document_id: str, new_text_content: str, company_id: int, title: Optional[str] = None, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Deletes existing embeddings for a document in the RAG index.
        The re-embedding process is handled by a separate Celery task.
        """
        # First, delete existing embeddings for the document
        # We use document_id for deletion as it's the primary identifier.
        delete_result = await self.delete_document_by_id(document_id, company_id)
        if delete_result.get("status") == "failed":
            return delete_result # Or handle error appropriately

        # The actual embedding and upserting will be handled by a Celery task.
        # This function now only handles the deletion part.
        return {"status": "success", "message": "Old embeddings deleted. Embedding task will be triggered separately."}

    async def get_relevant_context(self, query: str, company_id: int, n_results: int = 5) -> Dict[str, Any]:
        namespace = self._get_namespace(company_id)
        query_embedding = await asyncio.to_thread(self.embedding_model.encode, query)
        query_embedding = query_embedding.tolist()
        response = await asyncio.to_thread(self.index.query,
            vector=query_embedding,
            top_k=n_results,
            include_metadata=True,
            namespace=namespace
        )
        
        context_str = ""
        document_ids = []
        top_score_percent: Optional[float] = None
        
        if response.get('matches'):
            context_list = []
            scores = []
            for match in response['matches']:
                if 'score' in match:
                    scores.append(match['score'])
                if 'content' in match['metadata']:
                    context_list.append(match['metadata']['content'])
                if 'document_id' in match['metadata']:
                    document_ids.append(match['metadata']['document_id'])
            
            context_str = "\n".join(context_list)
            document_ids = list(set(document_ids))
            if scores:
                top_score = max(scores)
                # Convert to percentage for easier downstream consumption
                top_score_percent = float(top_score) * 100

        return {
            "context": context_str,
            "document_ids": document_ids,
            "match_score": top_score_percent,
        }

    async def add_documents(self, documents: List[str], company_id: int, source_filename: str, document_id: str, tags: Optional[List[str]] = None):
        namespace = self._get_namespace(company_id)
        embeddings = await asyncio.to_thread(self.embedding_model.encode, documents)
        embeddings = embeddings.tolist()
        vectors_to_upsert = []
        for doc, emb in zip(documents, embeddings):
            vector_id = str(uuid.uuid4())
            metadata = {'source': source_filename, 'content': doc, 'document_id': document_id}
            if tags:
                metadata['tags'] = tags
            vectors_to_upsert.append((vector_id, emb, metadata))
        await asyncio.to_thread(self.index.upsert, vectors=vectors_to_upsert, namespace=namespace)

    def _chunk_text(self, text_content: str) -> List[str]:
        if not text_content or not text_content.strip():
            return []
        chunk_size = 1000
        overlap = 200
        return [text_content[i:i + chunk_size] for i in range(0, len(text_content), chunk_size - overlap)]

    async def add_text_as_document(self, text_content: str, file_name: str, company_id: int, document_id: str, tags: Optional[List[str]] = None) -> Dict[str, Any]:
        chunks = self._chunk_text(text_content)
        if not chunks:
            return {"status": "failed", "message": "Could not chunk document text."}
        await self.add_documents(chunks, company_id, file_name, document_id, tags=tags)
        return {"status": "success", "chunks_added": len(chunks)}

# Global singleton instance, created on import
rag_service = RAGService()
