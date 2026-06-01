from typing import Optional
import threading

from vlmaps.llm.base import LLMProvider
from vlmaps.llm.config import LLMConfig, get_api_key_from_env, load_llm_config
from vlmaps.llm.providers.openai_provider import OpenAIProvider
from vlmaps.llm.providers.jazari_provider import JazariProvider

_PROVIDER: Optional[LLMProvider] = None
_PROVIDER_LOCK = threading.Lock()


def create_llm_provider(config: LLMConfig, api_key: Optional[str] = None) -> LLMProvider:
    provider = config.provider.lower()
    key = api_key or get_api_key_from_env(provider)

    if provider == "openai" and config.openai:
        return OpenAIProvider(api_key=key, config=config.openai)
    elif provider == "jazari" and config.jazari:
        return JazariProvider(api_key=key, config=config.jazari)

    raise ValueError(f"Unsupported LLM provider '{config.provider}'")


def get_llm_provider(config_path: Optional[str] = None, api_key: Optional[str] = None) -> LLMProvider:
    global _PROVIDER
    if _PROVIDER is not None:
        return _PROVIDER

    with _PROVIDER_LOCK:
        if _PROVIDER is None:
            config = load_llm_config(config_path)
            _PROVIDER = create_llm_provider(config, api_key=api_key)

    return _PROVIDER

