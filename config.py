"""Centralized configuration loaded from environment variables."""

import os
import warnings
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from pydantic_settings import BaseSettings

_BASE_DIR: Path = Path(__file__).resolve().parent
load_dotenv(_BASE_DIR / ".env")


class Settings(BaseSettings):
    """Application settings sourced from environment variables."""

    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str = ""
    llm_model: str = "gpt-4o"

    image_api_url: str = "https://api.openai.com/v1"
    image_api_key: str = ""
    image_model: str = "dall-e-3"

    audio_api_url: str = "https://api.openai.com/v1"
    audio_api_key: str = ""
    audio_model: str = "tts-1"

    app_host: str = "0.0.0.0"
    app_port: int = 8000
    generated_dir: str = "generated"

    model_config = {
        "env_file": str(_BASE_DIR / ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


def _validate_settings(s: Settings) -> None:
    """Warn if critical keys still hold placeholder values."""
    placeholder_prefixes = ("sk-your", "your-", "changeme")
    if any(s.llm_api_key.lower().startswith(p) for p in placeholder_prefixes):
        warnings.warn(
            "LLM_API_KEY appears to be a placeholder. "
            "Set a real API key in .env before making LLM calls.",
            UserWarning,
            stacklevel=2,
        )
    if any(s.image_api_key.lower().startswith(p) for p in placeholder_prefixes):
        warnings.warn(
            "IMAGE_API_KEY appears to be a placeholder. "
            "Set a real API key in .env before making image generation calls.",
            UserWarning,
            stacklevel=2,
        )


settings = Settings()
_validate_settings(settings)


def is_configured(value: str) -> bool:
    """Check if an API key is actually set (not placeholder)."""
    if not value:
        return False
    placeholder_prefixes = ("sk-your", "your-", "changeme")
    return not any(value.lower().startswith(p) for p in placeholder_prefixes)


def update_settings(updates: dict[str, str | None]) -> None:
    """Update settings at runtime from user-provided values."""
    global settings
    for key, value in updates.items():
        if value is not None and hasattr(settings, key):
            setattr(settings, key, value)
    import client
    client.llm_client = client.LLMClient()
