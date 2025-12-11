from abc import ABC, abstractmethod
from typing import List, Dict


class LLMProvider(ABC):
    """Abstract provider with project-specific LLM operations."""

    @abstractmethod
    def parse_object_goal_instruction(self, messages: List[Dict[str, str]]) -> str:
        ...

    @abstractmethod
    def parse_spatial_instruction(self, messages: List[Dict[str, str]]) -> str:
        ...

    @abstractmethod
    def find_similar_category(self, messages: List[Dict[str, str]]) -> str:
        ...

