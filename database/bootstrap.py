from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Source
from parsers.registry import get_source_payloads


DEFAULT_SOURCES = get_source_payloads()


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
