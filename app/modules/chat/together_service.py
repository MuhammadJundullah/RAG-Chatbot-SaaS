import json
from datetime import date
from typing import Optional, AsyncGenerator, List

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import user_model, company_model


class TogetherService:
    def __init__(self):
        self.api_key = settings.TOGETHER_API_KEY
        self.model = settings.TOGETHER_MODEL
        self.base_url = "https://api.together.xyz/v1/chat/completions"

    async def generate_chat_response(
        self,
        question: str,
        db: AsyncSession,
        current_user: user_model.Users,
        context: Optional[str] = None,
        conversation_history: Optional[list[dict]] = None,
        model_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        """
        Generates a streamed chat response using Together AI, enriched with company/role context.
        """
        company = await db.get(company_model.Company, current_user.company_id)
        company_name = company.name if company else "your company"

        role_name = current_user.role if current_user.role else "employee"

        division_name = "general"
        if current_user and current_user.division:
            if isinstance(current_user.division, str):
                division_name = current_user.division
            elif hasattr(current_user.division, "name"):
                division_name = current_user.division.name

        system_instruction = f"""You are a specialized AI business assistant for {company_name}. Your role is to help employees by answering questions and providing data-driven insights.

        Your core instructions are:
        0.  **Identity:** Your name is Orbit. If the user asks who you are or greets you, you should recognize that your name is Orbit.
        1.  **Language:** Always answer with indonesian language. 
        2.  **Strictly Data-Bound:** Your ONLY source of information is the content provided below under "BEGIN DOCUMENTS". You MUST NOT use any of your own general knowledge.
        3.  **Act as an Analyst:** If the user asks for summaries, analysis, recommendations, or strategic advice (e.g., "how to improve sales", "what are the key trends"), act as a helpful business analyst. Analyze the data provided and formulate your response based SOLEly on that data. When relevant, use today's date ({date.today().isoformat()}) to provide more insightful context, for example, by comparing past data to the current period.
        4.  **Role Awareness:** You are speaking to an employee with the role: {role_name} in the {division_name} division.
        5.  **Natural and Conversational Tone:** Respond in a natural, conversational, and helpful manner. Avoid robotic or overly formal language, and do not explicitly state that your answers are "based on the provided documents" or similar phrases.
        """

        messages: List[dict] = [{"role": "system", "content": system_instruction}]

        if conversation_history:
            for entry in conversation_history:
                messages.append({"role": "user", "content": entry["question"]})
                messages.append({"role": "assistant", "content": entry["answer"]})

        prompt_sections: List[str] = []
        if context:
            prompt_sections.append(f"---BEGIN DOCUMENTS---\n{context}\n---END DOCUMENTS---")
        prompt_sections.append(f"Based ONLY on the context provided above, answer this question: {question}")

        messages.append({"role": "user", "content": "\n\n".join(prompt_sections)})

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model_name or self.model,
            "messages": messages,
            "temperature": 0.1,
            "stream": True,
        }

        try:
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream("POST", self.base_url, headers=headers, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not line or not line.startswith("data:"):
                            continue
                        data = line[len("data:"):].strip()
                        if data == "[DONE]":
                            break
                        try:
                            parsed = json.loads(data)
                        except json.JSONDecodeError:
                            continue
                        choices = parsed.get("choices", [])
                        if not choices:
                            continue
                        delta = choices[0].get("delta", {})
                        content = delta.get("content")
                        if content:
                            yield content
        except Exception as e:
            # Keep behavior similar to previous service by logging and yielding nothing else.
            print(f"Together chat stream error: {str(e)}")

    async def recommend_topics_for_division(
        self,
        db: AsyncSession,
        current_user: user_model.Users,
    ) -> List[str]:
        """
        Generate 5 short topics (1-2 words) relevant to the user's division.
        """
        company = await db.get(company_model.Company, current_user.company_id)
        company_name = company.name if company else "your company"
        division_label = current_user.division or "general"
        role_name = current_user.role or "employee"

        prompt = (
            f"You are drafting discussion topics for an employee in the {division_label} division "
            f"at {company_name} (role: {role_name}). "
            "Provide exactly 5 concise topics (2-3 words each), comma-separated only. "
            "No numbering, no extra text. Using Indonesian language"
        )

        response_text = ""
        async for chunk in self.generate_chat_response(
            question=prompt,
            db=db,
            current_user=current_user,
            context=None,
            conversation_history=[],
            model_name=None,
        ):
            response_text += chunk

        normalized = response_text.replace(";", ",").replace("\n", ",")
        topics = [t.strip(" -•\t") for t in normalized.split(",") if t.strip()]
        return topics[:5]


together_service = TogetherService()
