import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.config.settings import settings
from typing import Optional, AsyncGenerator
from app.database import schema
from datetime import date

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def should_query_database(self, question: str, schema_info: str) -> bool:
        """
        Uses the LLM to determine if a user's question is likely to be answerable
        by querying the company's database schema.
        """
        prompt = f"""
        You are a decision-making AI. Your task is to determine if a user's question can be answered using a SQL query on a database with the given schema.

        **Database Schema:**
        {schema_info}

        **User's Question:**
        {question}

        **Instructions:**
        - Analyze the user's question and the database schema.
        - If the question can be answered using data in the database, then a database query is appropriate.
        - If the question is general, conversational, or asks for information not present in the schema (e.g., "hello", "what is the company's mission?", "explain this SOP document"), then a database query is not needed.
        - Respond with a single word: "Yes" or "No".

        **Decision (Yes/No):**
        """

        try:
            response = await self.model.generate_content_async(prompt)
            decision = response.text.strip().lower()
            return "yes" in decision
        except Exception as e:
            print(f"Gemini 'should_query_database' decision error: {e}")
            return False

    async def generate_raw_sql_query(self, question: str, schema_info: str) -> Optional[str]:
        """
        Generates a raw, executable SQL query string based on the user's question and a given database schema.
        """
        prompt = f"""
        You are an expert SQL generator. Based on the database schema provided below, write a single, executable SQL query to answer the user's question.

        **IMPORTANT CONTEXT:**
        - Today's date is {date.today().isoformat()}.
        - When a user asks about a time period like "this month" or "last month", use today's date to calculate the correct date range for the SQL query.
        - For example, if today is 2025-05-11 and the user asks "sales this month", the WHERE clause should be something like \"WHERE date_column >= '2025-05-01' AND date_column < '2025-06-01'\".

        **Database Schema:**
        {schema_info}

        **User's Question:**
        {question}

        **Instructions:**
        1.  ONLY generate a single `SELECT` query.
        2.  Do NOT generate any `INSERT`, `UPDATE`, `DELETE`, or any other type of query.
        3.  The query should be a single line of text.
        4.  Do not add any explanation, comments, or markdown formatting. Just the raw SQL.

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
        db: AsyncSession,
        current_user: schema.Users,
        context: Optional[str] = None, 
        query_results: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates a final chat response as a stream, personalizing the prompt with company-specific details.
        """
        # Get company name
        company = await db.get(schema.Company, current_user.Companyid)
        company_name = company.name if company else "your company"

        # Get role name
        role_name = current_user.role if current_user.role else "employee"

        system_instruction = f"""You are a specialized AI business assistant for {company_name}. Your role is to help employees by answering questions and providing data-driven insights.

Your core instructions are:
1.  **Strictly Data-Bound:** Your ONLY source of information is the content provided below under \"BEGIN DOCUMENTS\" and \"BEGIN DATABASE RESULTS\". You MUST NOT use any of your own general knowledge.
2.  **Act as an Analyst:** If the user asks for summaries, analysis, recommendations, or strategic advice (e.g., "how to improve sales", "what are the key trends"), act as a helpful business analyst. Analyze the data provided and formulate your response based SOLEly on that data. When relevant, use today's date ({date.today().isoformat()}) to provide more insightful context, for example, by comparing past data to the current period.
3.  **Role Awareness:** You are speaking to an employee with the role: {role_name}.
"""

        prompt_parts = [system_instruction]

        if context:
            prompt_parts.append(f"---BEGIN DOCUMENTS---\n{context}\n---END DOCUMENTS---")

        if query_results:
            prompt_parts.append(f"---BEGIN DATABASE RESULTS---\n{query_results}\n---END DATABASE RESULTS---")

        prompt_parts.append(f"Based ONLY on the context provided above, answer this question: {question}")

        try:
            generation_config = genai.GenerationConfig(temperature=0.5)
            response_stream = await self.model.generate_content_async(
                prompt_parts, 
                stream=True,
                generation_config=generation_config
            )
            async for chunk in response_stream:
                yield chunk.text
        except Exception as e:
            print(f"Gemini chat stream error: {str(e)}")

gemini_service = GeminiService()