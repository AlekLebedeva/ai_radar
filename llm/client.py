"""
AI Radar — LLM API Client
Supports OpenAI-compatible APIs (OpenAI, local LLMs, etc.)
"""

import os
import asyncio
from typing import Optional, Dict, Any

import aiohttp


class LLMClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o-mini",
        timeout: int = 60,
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout

    async def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int = 2000,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Send chat completion request."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if response_format:
            payload["response_format"] = response_format

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout),
            ) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"LLM API error {resp.status}: {text}")
                data = await resp.json()
                return data["choices"][0]["message"]["content"]

    async def classify(self, title: str, description: str, tags: list[str]) -> Dict[str, Any]:
        """Classify model domain using LLM."""
        from llm.prompts import CLASSIFY_PROMPT

        prompt = CLASSIFY_PROMPT.format(
            title=title,
            description=description or "",
            tags=", ".join(tags) if tags else "",
        )
        messages = [
            {"role": "system", "content": "You are an AI model classification expert. Return ONLY valid JSON."},
            {"role": "user", "content": prompt},
        ]
        raw = await self.chat(messages, response_format={"type": "json_object"})
        import json
        return json.loads(raw)

    async def summarize(self, title: str, description: str) -> Dict[str, str]:
        """Generate EN and RU summaries."""
        from llm.prompts import SUMMARIZE_PROMPT

        prompt = SUMMARIZE_PROMPT.format(title=title, description=description or "")
        messages = [
            {"role": "system", "content": "You are a technical writer. Return ONLY valid JSON with en and ru fields."},
            {"role": "user", "content": prompt},
        ]
        raw = await self.chat(messages, response_format={"type": "json_object"})
        import json
        return json.loads(raw)