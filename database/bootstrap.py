from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Source


DEFAULT_SOURCES = [
    {
        "id": "huggingface",
        "name": "Hugging Face",
        "code": "huggingface",
        "api_base_url": "https://huggingface.co/api",
        "api_doc_url": "https://huggingface.co/docs/hub/api",
        "auth_type": "token_header",
        "rate_limit": {"rpm": 100},
        "is_active": True,
    },
    {
        "id": "reddit",
        "name": "Reddit",
        "code": "reddit",
        "api_base_url": "https://oauth.reddit.com",
        "api_doc_url": "https://www.reddit.com/dev/api",
        "auth_type": "oauth2",
        "rate_limit": {"rpm": 60},
        "is_active": True,
    },
    {
        "id": "github",
        "name": "GitHub",
        "code": "github",
        "api_base_url": "https://api.github.com",
        "api_doc_url": "https://docs.github.com/en/rest",
        "auth_type": "token_header",
        "rate_limit": {"rpm": 30},
        "is_active": True,
    },
    {
        "id": "arxiv",
        "name": "arXiv",
        "code": "arxiv",
        "api_base_url": "http://export.arxiv.org/api",
        "api_doc_url": "https://arxiv.org/help/api",
        "auth_type": "none",
        "rate_limit": {"rpm": 20},
        "is_active": True,
    },
    {
        "id": "pypi",
        "name": "PyPI",
        "code": "pypi",
        "api_base_url": "https://pypi.org/pypi",
        "api_doc_url": "https://docs.pypi.org/api",
        "auth_type": "none",
        "rate_limit": {"rpm": 60},
        "is_active": True,
    },
    {
        "id": "web",
        "name": "Web/Reddit Mock",
        "code": "web",
        "api_base_url": "",
        "api_doc_url": "",
        "auth_type": "none",
        "rate_limit": {"rpm": 30},
        "is_active": True,
    },
]


async def seed_default_sources(db: AsyncSession) -> None:
    for payload in DEFAULT_SOURCES:
        result = await db.execute(select(Source).where(Source.code == payload["code"]))
        source = result.scalar_one_or_none()
        if source is None:
            db.add(Source(**payload))
            continue

        for key, value in payload.items():
            if key != "id":
                setattr(source, key, value)

    await db.commit()
