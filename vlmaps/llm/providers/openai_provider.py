import openai
from typing import List, Dict, Optional
from vlmaps.llm.base import LLMProvider
from vlmaps.llm.config import OpenAIConfig

class OpenAIProvider(LLMProvider):
    def __init__(self, api_key: Optional[str], config: OpenAIConfig):
        self.cfg = config
        self.client = openai.OpenAI(api_key=api_key, base_url=config.base_url, timeout=config.timeout)

    def find_similar_category(self, messages: List[Dict[str, str]]) -> str:
        cfg = self.cfg.find_similar_category
        response = self.client.chat.completions.create(
            **cfg,
            messages=messages,
        )
        return response.choices[0].message.content

    def parse_instruction(self, messages: List[Dict[str, str]]) -> str:
        cfg = self.cfg.parse_instruction
        response = self.client.chat.completions.create(
            **cfg,
            messages=messages,
        )
        return response.choices[0].message.content

