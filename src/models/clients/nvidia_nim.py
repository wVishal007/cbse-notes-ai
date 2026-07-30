from __future__ import annotations

from openai import OpenAI

from src.config.settings import get_settings
from src.models.clients.base import LLMClient, RateLimitError


class NvidiaNIMClient(LLMClient):
    def __init__(self, model: str = "nvidia/nemotron-3-ultra-550b-a55b"):
        settings = get_settings()
        self._client = OpenAI(
            api_key=settings.nvidia_nim_api_key,
            base_url="https://integrate.api.nvidia.com/v1",
        )
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
