from __future__ import annotations

from mistralai.client import Mistral
from mistralai.client.models.systemmessage import SystemMessage
from mistralai.client.models.usermessage import UserMessage

from src.config.settings import get_settings
from src.models.clients.base import LLMClient, RateLimitError


class MistralClient(LLMClient):
    def __init__(self, model: str = "mistral-medium"):
        settings = get_settings()
        self._client = Mistral(api_key=settings.mistral_api_key)
        super().__init__(model)

    def _call(self, system_prompt: str, user_prompt: str) -> str:
        try:
            response = self._client.chat.complete(
                model=self.model,
                messages=[
                    SystemMessage(content=system_prompt),
                    UserMessage(content=user_prompt),
                ],
            )
            return str(response.choices[0].message.content or "")
        except Exception as e:
            if "rate" in str(e).lower() or "too many" in str(e).lower():
                raise RateLimitError(str(e)) from e
            raise
