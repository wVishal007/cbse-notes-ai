from __future__ import annotations

from functools import lru_cache

from src.config.settings import get_settings


@lru_cache
def get_model_for_node(node_name: str) -> tuple[str, str]:
    settings = get_settings()
    return settings.get_model_for_node(node_name)


def create_client(node_name: str):
    """Factory: returns the right LLM client for the given node based on its configured provider."""
    provider, model = get_model_for_node(node_name)

    if provider == "google":
        from src.models.clients.gemini import GeminiClient
        return GeminiClient(model=model)
    elif provider == "mistral":
        from src.models.clients.mistral import MistralClient
        return MistralClient(model=model)
    elif provider == "nvidia_nim":
        from src.models.clients.nvidia_nim import NvidiaNIMClient
        return NvidiaNIMClient(model=model)
    elif provider == "groq":
        from src.models.clients.groq import GroqClient
        return GroqClient(model=model)
    else:
        raise ValueError(f"Unknown provider '{provider}' for node '{node_name}'")


def list_available_providers() -> dict[str, bool]:
    settings = get_settings()
    return {
        "mistral": bool(settings.mistral_api_key),
        "google": bool(settings.google_api_key),
        "groq": bool(settings.groq_api_key),
        "nvidia_nim": bool(settings.nvidia_nim_api_key),
        "openai": bool(settings.openai_api_key),
    }
