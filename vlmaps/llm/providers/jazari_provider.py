import json
import urllib.request
import urllib.error
from typing import List, Dict, Optional

from vlmaps.llm.base import LLMProvider
from vlmaps.llm.config import JazariConfig


class JazariProvider(LLMProvider):
    def __init__(self, api_key: Optional[str], config: JazariConfig):
        self.cfg = config
        self.api_key = api_key
        # Ensure base url has no trailing slash to append /v1/parse safely
        self.base_url = config.base_url.rstrip("/") if config.base_url else "http://localhost:8000"

    def _call_api(self, messages: List[Dict[str, str]], **kwargs) -> str:
        url = f"{self.base_url}/v1/parse"
        
        # Prepare the payload according to OpenAPI spec
        payload = {
            "messages": messages,
            **kwargs
        }
        
        data = json.dumps(payload).encode("utf-8")
        
        headers = {
            "Content-Type": "application/json"
        }
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        
        try:
            with urllib.request.urlopen(req, timeout=self.cfg.timeout or 60.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("raw", "")
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise Exception(f"Jazari API Error {e.code}: {error_body}")
        except Exception as e:
            raise Exception(f"Failed to communicate with Jazari API: {e}")

    def find_similar_category(self, messages: List[Dict[str, str]]) -> str:
        cfg = self.cfg.find_similar_category or {}
        return self._call_api(messages, **cfg)

    def parse_instruction(self, messages: List[Dict[str, str]]) -> str:
        cfg = self.cfg.parse_instruction or {}
        return self._call_api(messages, **cfg)
