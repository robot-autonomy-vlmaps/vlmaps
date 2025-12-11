import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

import yaml


@dataclass
class OpenAIConfig:
    parse_object_goal_instruction: Dict[str, Any] = field(default_factory=dict)
    parse_spatial_instruction: Dict[str, Any] = field(default_factory=dict)
    find_similar_category: Dict[str, Any] = field(default_factory=dict)
    base_url: Optional[str] = None
    timeout: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    provider: str
    openai: Optional[OpenAIConfig] = None

def get_default_config_path(provider: Optional[str] = None) -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    return repo_root / "config" / "llm.yaml"


def load_llm_config(path: Optional[str] = None, provider: Optional[str] = None) -> LLMConfig:
    cfg_path = Path(path) if path else get_default_config_path(provider)
    if not cfg_path.exists():
        raise ValueError(f"LLM config file not found at {cfg_path}")

    with cfg_path.open("r") as f:
        data = yaml.safe_load(f) or {}

    provider_name = provider or data.get("provider")
    if not provider_name:
        raise ValueError("LLM config must specify 'provider'")

    if provider_name == "openai":
        provider_cfg = data.get("openai") or {}
        openai_cfg = OpenAIConfig(
            base_url=provider_cfg.get("base_url"),
            timeout=provider_cfg.get("timeout"),
            parse_object_goal_instruction=provider_cfg.get("parse_object_goal_instruction", {}) or {},
            parse_spatial_instruction=provider_cfg.get("parse_spatial_instruction", {}) or {},
            find_similar_category=provider_cfg.get("find_similar_category", {}) or {},
            extra=provider_cfg.get("extra", {}) or {},
        )
        return LLMConfig(provider=provider_name, openai=openai_cfg)

    raise ValueError(f"Unsupported LLM provider config '{provider_name}'")


def get_api_key_from_env(provider: str) -> str:
    env_name = f"VLMAPS_LLM_KEY_{provider.upper()}"
    api_key = os.environ.get(env_name)
    if not api_key:
        raise ValueError(f"API key not found in environment variable {env_name}")
    return api_key

