"""Helpers for configuring OpenAI-compatible LLM clients.

This project historically relied on hosted OpenAI models. To support local
LLM servers that expose an OpenAI-compatible API (e.g. Ollama, vLLM,
text-generation-inference), we centralize the client construction and model
selection logic here.
"""

from __future__ import annotations

import os
from functools import lru_cache
from typing import Optional

from openai import OpenAI


DEFAULT_CHAT_MODEL = "gpt-4-turbo"
DEFAULT_COMPLETION_MODEL = "gpt-3.5-turbo-instruct"


def _get_env(*keys: str, default: Optional[str] = None) -> Optional[str]:
    for key in keys:
        value = os.getenv(key)
        if value:
            return value
    return default


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """Return a configured OpenAI client with optional base-url override."""
    api_key = _get_env(
        "VLMAPS_LLM_API_KEY",
        "OPENAI_KEY",
        "OPENAI_API_KEY",
        default="EMPTY",
    )
    base_url = _get_env(
        "VLMAPS_LLM_BASE_URL",
        "OPENAI_API_BASE",
        "OPENAI_BASE_URL",
    )
    organization = _get_env("OPENAI_ORG", "OPENAI_ORGANIZATION")

    client_kwargs = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url.rstrip("/")
    if organization:
        client_kwargs["organization"] = organization
    return OpenAI(**client_kwargs)


def get_chat_model_name() -> str:
    """Return preferred chat-completions model name."""
    return _get_env(
        "VLMAPS_LLM_CHAT_MODEL",
        "OPENAI_CHAT_MODEL",
        "OPENAI_MODEL",
        default=DEFAULT_CHAT_MODEL,
    )


def get_completion_model_name() -> str:
    """Return preferred completions model name."""
    return _get_env(
        "VLMAPS_LLM_COMPLETION_MODEL",
        "OPENAI_COMPLETION_MODEL",
        default=DEFAULT_COMPLETION_MODEL,
    )


