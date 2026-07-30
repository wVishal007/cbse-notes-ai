from __future__ import annotations

from google import genai

from src.config.settings import get_settings
from src.models.clients.base import LLMClient, RateLimitError


class GeminiClient(LLMClient):
    def __init__(self, model: str = "models/gemini-3.5-flash-lite"):
        settings = get_settings()
        self._client = genai.Client(api_key=settings.google_api_key)
        super().__init__(model)

    def _call(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=user_prompt,
                config={"system_instruction": system_prompt},
            )
            return response.text or ""
        except Exception as e:
            if "rate" in str(e).lower() or "too many" in str(e).lower():
                raise RateLimitError(str(e)) from e
            raise
