"""
AI Radar — LLM Processing Module
Enrichment of raw data with LLM-generated metadata.
"""
from llm.client import LLMClient
from llm.processor import LLMProcessor

__all__ = ["LLMClient", "LLMProcessor"]