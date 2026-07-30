from __future__ import annotations

from functools import lru_cache

from src.config.settings import get_settings


@lru_cache
def get_model_for_node(node_name: str) -> tuple[str, str]:
    settings = get_settings()
    return settings.get_model_for_node(node_name)


def list_available_providers() -> dict[str, bool]:
    settings = get_settings()
    return {
        "mistral": bool(settings.mistral_api_key),
        "google": bool(settings.google_api_key),
        "groq": bool(settings.groq_api_key),
        "nvidia_nim": bool(settings.nvidia_nim_api_key),
        "openai": bool(settings.openai_api_key),
    }
