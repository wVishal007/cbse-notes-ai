from __future__ import annotations

from groq import Groq

from src.config.settings import get_settings
from src.models.clients.base import LLMClient, RateLimitError


class GroqClient(LLMClient):
    def __init__(self, model: str = "llama-3.3-70b-versatile"):
        settings = get_settings()
        self._client = Groq(api_key=settings.groq_api_key)
        super().__init__(model)

    def _call(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            )
            return response.choices[0].message.content or ""
        except Exception as e:
            if "rate" in str(e).lower() or "too many" in str(e).lower():
                raise RateLimitError(str(e)) from e
            raise
