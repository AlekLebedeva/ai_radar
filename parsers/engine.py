import asyncio
import hashlib
from datetime import datetime, timezone
from typing import Any, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Source, ParserTask, ParserLog, RawItem
from database.session import is_postgres
from admin.service import TaskService, LogService
from parsers.base import BaseParser
from parsers.adapters import HuggingFaceAdapter, RedditAdapter


class MockHuggingFaceParser(BaseParser):
    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id=None):
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
    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id=None):
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
    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id=None):
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
    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id=None):
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
    async def fetch(self, date_from, date_to, filters=None, max_items=1000, task_id=None):
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
    "huggingface": HuggingFaceAdapter(),
    "reddit": RedditAdapter(),
    "github": MockGitHubParser("github", "GitHub", "https://api.github.com"),
    "arxiv": MockArxivParser("arxiv", "arXiv", "http://export.arxiv.org/api"),
    "pypi": MockPyPIParser("pypi", "PyPI", "https://pypi.org/pypi"),
    "web": MockWebParser("web", "Web/Reddit", ""),
}


def _json_safe(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, UUID):
        return str(value)
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if hasattr(value, "model_dump"):
        return _json_safe(value.model_dump())
    if hasattr(value, "to_dict"):
        return _json_safe(value.to_dict())
    if hasattr(value, "__dict__"):
        return _json_safe(
            {
                key: item
                for key, item in value.__dict__.items()
                if not key.startswith("_")
            }
        )
    return str(value)


def _datetime_safe(value: Any) -> Optional[datetime]:
    if value is None or isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is not None:
            return parsed.astimezone(timezone.utc).replace(tzinfo=None)
        return parsed
    return None


def _array_safe(value: Any) -> Any:
    if is_postgres() or value is None:
        return value
    return None


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

        source_result = await self.db.execute(select(Source).where(Source.code == task.parser_name))
        source = source_result.scalar_one_or_none()
        if not source:
            await self.task_svc.update_status(task_id, "failed", error=f"Source not found: {task.parser_name}")
            return

        log = ParserLog(
            parser_name=task.parser_name,
            task_id=task_id,
            status="running",
        )
        self.db.add(log)
        await self.db.commit()
        await self.db.refresh(log)

        await self.task_svc.update_status(task_id, "running")

        try:
            raw_data = await parser.fetch(
                date_from=task.date_from,
                date_to=task.date_to,
                filters=task.filters,
                max_items=task.max_items or 1000,
                task_id=task.id,
            )

            items_collected = len(raw_data)
            items_new = 0

            for item in raw_data:
                normalized = parser.normalize(item)
                if not all(normalized.get(key) for key in ("external_id", "title", "url")):
                    continue
                item_hash = hashlib.sha256(
                    f"{normalized['url']}:{normalized['external_id']}".encode()
                ).hexdigest()

                dup_check = await self.db.execute(
                    select(RawItem).where(RawItem.hash == item_hash)
                )
                if dup_check.scalar_one_or_none():
                    continue

                raw_item = RawItem(
                    source_id=source.id,
                    task_id=task_id,
                    external_id=normalized["external_id"],
                    title=normalized["title"],
                    model_type=normalized.get("model_type"),
                    domain=_array_safe(normalized.get("domain")),
                    description=normalized.get("description"),
                    url=normalized["url"],
                    author=normalized.get("author"),
                    license=normalized.get("license"),
                    tags=_array_safe(normalized.get("tags")),
                    popularity_metric=normalized.get("popularity_metric"),
                    created_at_source=_datetime_safe(normalized.get("created_at_source")),
                    updated_at_source=_datetime_safe(normalized.get("updated_at_source")),
                    language=_array_safe(normalized.get("language")),
                    framework=_array_safe(normalized.get("framework")),
                    task_type=_array_safe(normalized.get("task_type")),
                    raw_json=_json_safe(normalized),
                    hash=item_hash,
                    status=normalized.get("status") or "raw",
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
