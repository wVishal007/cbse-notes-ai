from __future__ import annotations

import os
from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # API Keys
    mistral_api_key: str = ""
    google_api_key: str = ""
    groq_api_key: str = ""
    nvidia_nim_api_key: str = ""
    openai_api_key: str = ""

    # LangSmith
    langchain_tracing_v2: bool = True
    langchain_api_key: str = ""
    langchain_project: str = "cbse-notes-ai"

    # Application
    log_level: str = "INFO"
    max_retries: int = 2
    cache_ttl_hours: int = 168

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_model_for_node(self, node_name: str) -> tuple[str, str]:
        provider_override = os.environ.get(f"{node_name.upper()}__PROVIDER")
        model_override = os.environ.get(f"{node_name.upper()}__MODEL")

        if provider_override and model_override:
            return (provider_override.lower(), model_override)

        return DEFAULT_MODEL_MAP[node_name]


DEFAULT_MODEL_MAP: dict[str, tuple[str, str]] = {
    "planner": ("google", "models/gemini-3.1-flash-lite"),
    "research_search": ("google", "models/gemini-3.1-flash-lite"),
    "research_scrape": ("nvidia_nim", "nemotron-3-8b"),
    "aggregator": ("google", "models/gemini-3.1-flash-lite"),
    "synthesizer": ("mistral", "mistral-medium"),
    "validator": ("google", "models/gemini-3.1-flash-lite"),
    "pyq_agent": ("google", "models/gemini-3.5-flash-lite"),
    "formatter": ("google", "models/gemini-3.5-flash-lite"),
}


SUPPORTED_CLASSES = [str(i) for i in range(1, 13)]
SUPPORTED_MEDIA: list[Literal["english", "hindi"]] = ["english", "hindi"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
