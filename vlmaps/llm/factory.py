from typing import Optional

from vlmaps.llm.base import LLMProvider
from vlmaps.llm.config import LLMConfig, get_api_key_from_env, load_llm_config
from vlmaps.llm.providers.openai_provider import OpenAIProvider

_PROVIDER: Optional[LLMProvider] = None


def create_llm_provider(config: LLMConfig, api_key: Optional[str] = None) -> LLMProvider:
    provider = config.provider.lower()
    key = api_key or get_api_key_from_env(provider)

    if provider == "openai" and config.openai:
        return OpenAIProvider(api_key=key, config=config.openai)

    raise ValueError(f"Unsupported LLM provider '{config.provider}'")


def get_llm_provider(config_path: Optional[str] = None, api_key: Optional[str] = None) -> LLMProvider:
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER

    config = load_llm_config(config_path)
    _PROVIDER = create_llm_provider(config, api_key=api_key)
    return _PROVIDER

