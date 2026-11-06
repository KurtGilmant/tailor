"""Passerelle LLM : fournisseurs interchangeables, sorties structurées, garde-fous."""

from tailor.llm.config import LLMConfig, Task
from tailor.llm.gateway import LLMGateway

__all__ = ["LLMConfig", "LLMGateway", "Task"]
