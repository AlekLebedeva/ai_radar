"""
AI Radar — GitHub Parser.

Сбор AI-репозиториев через GitHub Search API.
Адаптировано из ветки dvb.
"""

import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Optional

import httpx

logger = logging.getLogger("ai_radar.github")

GITHUB_API_BASE = "https://api.github.com"
GITHUB_TOKEN = ""

AI_TOPICS = [
    "llm", "machine-learning", "deep-learning", "transformer",
    "computer-vision", "nlp", "generative-ai", "diffusion-model",
    "reinforcement-learning", "rag", "langchain", "ai-agent",
]

TOPIC_DOMAIN_MAP = {
    "computer-vision": "CV", "object-detection": "CV", "image-classification": "CV",
    "nlp": "NLP", "llm": "NLP", "text-generation": "NLP",
    "speech-recognition": "Audio", "text-to-speech": "Audio",
    "reinforcement-learning": "RL",
    "multimodal": "Multimodal",
    "rag": "RAG", "langchain": "RAG",
}


class GitHubParser:
    def __init__(self):
        self._client: Optional[httpx.Client] = None

    @property
    def client(self) -> httpx.Client:
        if self._client is None:
            headers = {
                "Accept": "application/vnd.github+json",
                "User-Agent": "AI-Radar/1.0",
                "X-GitHub-Api-Version": "2022-11-28",
            }
            if GITHUB_TOKEN:
                headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
            self._client = httpx.Client(headers=headers, timeout=30)
        return self._client

    def fetch(self, date_from: datetime, date_to: datetime, filters: Optional[dict] = None, max_items: int = 1000) -> list[dict]:
        filters = filters or {}
        topics = filters.get("topics", AI_TOPICS[:3])
        min_stars = filters.get("min_stars", 10)
        sort = filters.get("sort", "stars")
        order = filters.get("order", "desc")

        date_str = date_from.strftime("%Y-%m-%d")
        topic_query = " ".join(f"topic:{t}" for t in topics[:3])
        query = f"{topic_query} stars:>={min_stars} pushed:>={date_str}"

        items = []
        page = 1
        per_page = min(filters.get("batch_size", 100), 100)

        while len(items) < max_items:
            try:
                resp = self.client.get(
                    f"{GITHUB_API_BASE}/search/repositories",
                    params={"q": query, "sort": sort, "order": order, "per_page": per_page, "page": page},
                )
                if resp.status_code == 403 and "rate limit" in resp.text.lower():
                    logger.warning("GitHub rate limit reached")
                    break
                resp.raise_for_status()
                data = resp.json()
            except Exception as e:
                logger.error("GitHub API error: %s", e)
                break

            repos = data.get("items", [])
            if not repos:
                break

            for repo in repos:
                item = self._normalize_repo(repo)
                items.append(item)

            page += 1
            if page > 10:
                break
            time.sleep(0.5)

        return items[:max_items]

    def _normalize_repo(self, repo: dict) -> dict:
        topics = repo.get("topics", [])
        topics_lower = {t.lower() for t in topics}
        language = repo.get("language") or ""

        domains = set()
        for t in topics:
            d = TOPIC_DOMAIN_MAP.get(t.lower())
            if d:
                domains.add(d)

        created_at = None
        if repo.get("created_at"):
            try:
                created_at = datetime.fromisoformat(repo["created_at"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        updated_at = None
        if repo.get("updated_at"):
            try:
                updated_at = datetime.fromisoformat(repo["updated_at"].replace("Z", "+00:00"))
            except (ValueError, TypeError):
                pass

        return {
            "external_id": repo.get("full_name", ""),
            "title": repo.get("name", ""),
            "description": repo.get("description") or "",
            "url": repo.get("html_url", ""),
            "author": repo.get("owner", {}).get("login", "") if repo.get("owner") else "",
            "license": (repo.get("license") or {}).get("spdx_id", "") if repo.get("license") else "",
            "tags": topics,
            "popularity_metric": repo.get("stargazers_count", 0),
            "domain": sorted(domains) or ["Other"],
            "model_type": "other",
            "language": [language] if language else [],
            "framework": [],
            "task_type": [],
            "created_at_source": created_at,
            "updated_at_source": updated_at,
        }
