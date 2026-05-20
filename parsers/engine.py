import asyncio
import hashlib
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ParserTask, ParserLog, RawItem
from admin.service import TaskService, LogService
from parsers.base import BaseParser


class MockHuggingFaceParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000):
        await asyncio.sleep(0.5)
        return [
            {
                "external_id": "microsoft/DialoGPT-medium",
                "title": "DialoGPT Medium",
                "model_type": "transformer",
                "domain": ["nlp", "chatbot"],
                "description": "Pre-trained model for conversational AI based on GPT-2.",
                "url": "https://huggingface.co/microsoft/DialoGPT-medium",
                "author": "Microsoft",
                "license": "mit",
                "tags": ["pytorch", "transformers", "nlp", "text-generation"],
                "popularity_metric": 5234,
                "created_at_source": "2023-08-15T10:30:00Z",
                "updated_at_source": "2025-11-20T14:22:00Z",
                "language": ["en"],
                "framework": ["PyTorch", "Transformers"],
                "task_type": ["text-generation"],
            }
        ]

    def normalize(self, raw_item):
        return raw_item


class MockGitHubParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000):
        await asyncio.sleep(0.5)
        return [
            {
                "external_id": "openai/whisper",
                "title": "Whisper",
                "model_type": "transformer",
                "domain": ["audio", "asr"],
                "description": "Robust speech recognition via large-scale weak supervision.",
                "url": "https://github.com/openai/whisper",
                "author": "OpenAI",
                "license": "mit",
                "tags": ["python", "pytorch", "speech-recognition", "audio"],
                "popularity_metric": 72000,
                "created_at_source": "2022-09-15T00:00:00Z",
                "updated_at_source": "2026-01-10T00:00:00Z",
                "language": ["en", "zh", "ru"],
                "framework": ["PyTorch"],
                "task_type": ["automatic-speech-recognition"],
            }
        ]

    def normalize(self, raw_item):
        return raw_item


class MockArxivParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000):
        await asyncio.sleep(0.5)
        return [
            {
                "external_id": "arxiv:2401.12345",
                "title": "Efficient Vision Transformers for Edge Devices",
                "model_type": "transformer",
                "domain": ["cv"],
                "description": "We propose a lightweight ViT architecture optimized for mobile deployment.",
                "url": "https://arxiv.org/abs/2401.12345",
                "author": "J. Smith et al.",
                "license": "arxiv",
                "tags": ["cv", "transformer", "edge-computing", "mobile"],
                "popularity_metric": 45,
                "created_at_source": "2024-01-15T00:00:00Z",
                "updated_at_source": "2024-01-15T00:00:00Z",
                "language": ["en"],
                "framework": ["PyTorch"],
                "task_type": ["image-classification"],
            }
        ]

    def normalize(self, raw_item):
        return raw_item


class MockPyPIParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000):
        await asyncio.sleep(0.3)
        return [
            {
                "external_id": "langchain",
                "title": "LangChain",
                "model_type": "library",
                "domain": ["nlp", "rag"],
                "description": "Building applications with LLMs through composability.",
                "url": "https://pypi.org/project/langchain",
                "author": "LangChain AI",
                "license": "mit",
                "tags": ["llm", "agents", "chains", "python"],
                "popularity_metric": 150000,
                "created_at_source": "2022-10-01T00:00:00Z",
                "updated_at_source": "2026-05-01T00:00:00Z",
                "language": ["en"],
                "framework": ["Python"],
                "task_type": ["framework"],
            }
        ]

    def normalize(self, raw_item):
        return raw_item


class MockWebParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000):
        await asyncio.sleep(0.3)
        return [
            {
                "external_id": "reddit_post_abc123",
                "title": "New Diffusion Model for 3D Generation",
                "model_type": "diffusion",
                "domain": ["cv", "generative"],
                "description": "Discussion of a new diffusion model capable of generating 3D assets from text.",
                "url": "https://reddit.com/r/MachineLearning/comments/abc123",
                "author": "u/ml_researcher",
                "license": None,
                "tags": ["diffusion", "3d-generation", "text-to-3d"],
                "popularity_metric": 1200,
                "created_at_source": "2026-05-10T00:00:00Z",
                "updated_at_source": "2026-05-10T00:00:00Z",
                "language": ["en"],
                "framework": [],
                "task_type": ["3d-generation"],
            }
        ]

    def normalize(self, raw_item):
        return raw_item


PARSER_REGISTRY = {
    "huggingface": MockHuggingFaceParser("huggingface", "HuggingFace", "https://huggingface.co/api"),
    "github": MockGitHubParser("github", "GitHub", "https://api.github.com"),
    "arxiv": MockArxivParser("arxiv", "arXiv", "http://export.arxiv.org/api"),
    "pypi": MockPyPIParser("pypi", "PyPI", "https://pypi.org/pypi"),
    "web": MockWebParser("web", "Web/Reddit", ""),
}


class ParserEngine:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.task_svc = TaskService(db)
        self.log_svc = LogService(db)

    async def run_task(self, task_id: UUID) -> None:
        result = await self.db.execute(select(ParserTask).where(ParserTask.id == task_id))
        task = result.scalar_one_or_none()
        if not task:
            return

        parser = PARSER_REGISTRY.get(task.parser_name)
        if not parser:
            await self.task_svc.update_status(task_id, "failed", error=f"Unknown parser: {task.parser_name}")
            return

        log = await self.log_svc.create(
            parser_name=task.parser_name,
            task_id=task_id,
            status="running",
        )

        await self.task_svc.update_status(task_id, "running")

        try:
            raw_data = await parser.fetch(
                date_from=task.date_from,
                date_to=task.date_to,
                filters=task.filters,
            )

            items_collected = len(raw_data)
            items_new = 0

            for item in raw_data:
                normalized = parser.normalize(item)
                item_hash = hashlib.sha256(
                    f"{normalized['url']}:{normalized['external_id']}".encode()
                ).hexdigest()

                dup_check = await self.db.execute(
                    select(RawItem).where(RawItem.hash == item_hash)
                )
                if dup_check.scalar_one_or_none():
                    continue

                raw_item = RawItem(
                    source_id=task.parser_name,
                    task_id=task_id,
                    external_id=normalized["external_id"],
                    title=normalized["title"],
                    model_type=normalized.get("model_type"),
                    domain=normalized.get("domain"),
                    description=normalized.get("description"),
                    url=normalized["url"],
                    author=normalized.get("author"),
                    license=normalized.get("license"),
                    tags=normalized.get("tags"),
                    popularity_metric=normalized.get("popularity_metric"),
                    created_at_source=normalized.get("created_at_source"),
                    updated_at_source=normalized.get("updated_at_source"),
                    language=normalized.get("language"),
                    framework=normalized.get("framework"),
                    task_type=normalized.get("task_type"),
                    raw_json=normalized,
                    hash=item_hash,
                    status="raw",
                )
                self.db.add(raw_item)
                items_new += 1

            await self.db.commit()

            log.status = "completed"
            log.items_count = items_collected
            log.duration_sec = int((datetime.utcnow() - log.run_at).total_seconds())
            await self.db.commit()

            await self.task_svc.update_status(
                task_id, "completed", items_collected=items_collected, items_new=items_new
            )

        except Exception as e:
            await self.db.rollback()
            log.status = "failed"
            log.errors_count = 1
            log.details = {"error": str(e)}
            await self.db.commit()
            await self.task_svc.update_status(task_id, "failed", error=str(e))
