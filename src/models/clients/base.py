from __future__ import annotations

import time
from abc import ABC, abstractmethod
from typing import Optional

from src.config.settings import get_settings


class RateLimitError(Exception):
    pass


class LLMClient(ABC):
    def __init__(self, model: str, max_retries: int | None = None, base_delay: float = 2.0):
        self.model = model
        settings = get_settings()
        self.max_retries = max_retries if max_retries is not None else settings.max_retries
        self.base_delay = base_delay

    @abstractmethod
    def _call(self, system_prompt: str, user_prompt: str) -> str:
        ...

    def invoke(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        for attempt in range(self.max_retries):
            try:
                return self._call(system_prompt, user_prompt)
            except RateLimitError:
                if attempt == self.max_retries - 1:
                    raise
                delay = self.base_delay * (2 ** attempt)
                time.sleep(delay)
            except Exception:
                if attempt == self.max_retries - 1:
                    raise
                time.sleep(self.base_delay)
        return None
