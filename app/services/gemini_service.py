import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import settings
from typing import List, Dict, Any, Optional
import json
from app import crud

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def generate_raw_sql_query(self, question: str, schema_info: str) -> Optional[str]:
        """
        Generates a raw, executable SQL query string based on the user's question and a given database schema.
        """
        prompt = f"""
        You are an expert SQL generator. Based on the database schema provided below, write a single, executable SQL query to answer the user's question.

        **Database Schema:**
        {schema_info}

        **User's Question:**
        {question}

        **Instructions:**
        1.  ONLY generate a single `SELECT` query.
        2.  Do NOT generate any `INSERT`, `UPDATE`, `DELETE`, or any other type of query.
        3.  The query should be a single line of text.
        4.  Do not add any explanation, comments, or markdown formatting. Just the raw SQL.
        5.  If the question cannot be answered with a SQL query based on the schema, return the text "NOT_POSSIBLE".

        **SQL Query:**
        """

        try:
            response = await self.model.generate_content_async(prompt)
            response_text = response.text.strip().replace('`', '').replace('\n', ' ')

            if "NOT_POSSIBLE" in response_text or not response_text.lower().strip().startswith("select"):
                return None

            return response_text
        except Exception as e:
            print(f"Gemini raw SQL generation error: {e}")
            return None

    async def generate_chat_response(
        self, 
        question: str, 
        company_id: int,
        user_role: str,
        db: AsyncSession,
        context: Optional[str] = None, 
        query_results: Optional[str] = None
    ) -> str:
        """
        Generates a final chat response, personalizing the prompt with company-specific details.
        """
        company = await db.get(crud.schema.Company, company_id)
        company_name = company.name if company else "your company"

        persona = f"You are a helpful AI assistant for {company_name}. Your role is to assist employees. You are speaking to an employee with the role: {user_role}."
        
        prompt_parts = [persona]

        if context:
            prompt_parts.append(f"Use the following internal company documents as your primary source of information:\n---BEGIN DOCUMENTS---\n{context}\n---END DOCUMENTS---")

        if query_results:
            prompt_parts.append(f"Additionally, here is some data retrieved from the company's internal database:\n---BEGIN DATABASE RESULTS---\n{query_results}\n---END DATABASE RESULTS---")

        prompt_parts.append(f"Based on the information provided, answer the following user question. If the information is not available in the documents or database, say that you do not have access to that information.\nUser Question: {question}")

        try:
            response = await self.model.generate_content_async(prompt_parts)
            return response.text
        except Exception as e:
            raise Exception(f"Gemini chat error: {str(e)}")

gemini_service = GeminiService()