import google.generativeai as genai
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from typing import Optional, AsyncGenerator
from app.models import user_model, company_model
from datetime import date

class GeminiService:
    def __init__(self):
        genai.configure(api_key=settings.GEMINI_API_KEY)
        self.model = genai.GenerativeModel(settings.GEMINI_MODEL)

    async def generate_chat_response(
        self, 
        question: str, 
        db: AsyncSession,
        current_user: user_model.Users,
        context: Optional[str] = None, 
        query_results: Optional[str] = None
    ) -> AsyncGenerator[str, None]:
        """
        Generates a final chat response as a stream, personalizing the prompt with company-specific details.
        """
        # Get company name
        company = await db.get(company_model.Company, current_user.company_id)
        company_name = company.name if company else "your company"

        # Get role name
        role_name = current_user.role if current_user.role else "employee"

        system_instruction = f"""You are a specialized AI business assistant for {company_name}. Your role is to help employees by answering questions and providing data-driven insights.

Your core instructions are:
1.  **Strictly Data-Bound:** Your ONLY source of information is the content provided below under \"BEGIN DOCUMENTS\". You MUST NOT use any of your own general knowledge.
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
            generation_config = genai.GenerationConfig(temperature=0.1)
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