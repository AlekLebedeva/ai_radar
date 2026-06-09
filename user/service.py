import uuid
from datetime import datetime
from typing import Dict, List, Optional

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from database.models import EnrichedItem, User, UserInterest, UserProfile
from user.schemas import (
    CategoryOut,
    UserInterestOut,
    UserOut,
    UserProfileOut,
)

CATEGORY_META: Dict[str, Dict[str, str]] = {
    "CV": {"label": "Computer Vision", "icon": "📷"},
    "NLP": {"label": "NLP", "icon": "💬"},
    "Audio": {"label": "Audio / Speech", "icon": "🎤"},
    "Multimodal": {"label": "Multimodal", "icon": "🎨"},
    "RL": {"label": "Reinforcement Learning", "icon": "🏆"},
    "Graph": {"label": "Graph Neural Networks", "icon": "🌐"},
    "Geo": {"label": "Geospatial / GIS", "icon": "🗺️"},
    "RAG": {"label": "RAG", "icon": "📖"},
    "Tabular": {"label": "Tabular Data", "icon": "📊"},
    "Generative": {"label": "Generative AI", "icon": "✨"},
    "Other": {"label": "Other", "icon": "📦"},
}


def _category_label(slug: str) -> str:
    meta = CATEGORY_META.get(slug)
    return meta["label"] if meta else slug


def _category_icon(slug: str) -> str:
    meta = CATEGORY_META.get(slug)
    return meta["icon"] if meta else "📌"


class CategoryService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_from_data(self) -> List[CategoryOut]:
        result = await self.db.execute(
            select(EnrichedItem.category, func.count())
            .where(
                EnrichedItem.category.isnot(None),
                EnrichedItem.category != "",
                EnrichedItem.processing_status == "completed",
            )
            .group_by(EnrichedItem.category)
            .order_by(func.count().desc())
        )
        rows = result.all()

        if rows:
            return [
                CategoryOut(
                    slug=slug,
                    label=_category_label(slug),
                    icon=_category_icon(slug),
                    item_count=count,
                )
                for slug, count in rows
            ]

        return [
            CategoryOut(slug=slug, label=meta["label"], icon=meta["icon"], item_count=0)
            for slug, meta in CATEGORY_META.items()
        ]


class UserService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_by_id(self, user_id: uuid.UUID) -> Optional[User]:
        result = await self.db.execute(
            select(User)
            .options(selectinload(User.profile), selectinload(User.interests))
            .where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, user_id: Optional[uuid.UUID] = None) -> User:
        if user_id is not None:
            user = await self.get_by_id(user_id)
            if user is not None:
                user.last_login = datetime.utcnow()
                await self.db.commit()
                await self.db.refresh(user)
                return user

        user = User(last_login=datetime.utcnow())
        profile = UserProfile(
            email_notifications=True,
            digest_frequency="daily",
            onboarding_completed=False,
        )
        user.profile = profile
        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)
        return await self.get_by_id(user.id)

    def _profile_out(self, profile: Optional[UserProfile]) -> UserProfileOut:
        if profile is None:
            return UserProfileOut()
        return UserProfileOut(
            display_name=profile.display_name,
            email=profile.email,
            email_notifications=profile.email_notifications,
            digest_frequency=profile.digest_frequency,
            onboarding_completed=profile.onboarding_completed,
        )

    def _interests_out(self, interests: List[UserInterest]) -> List[UserInterestOut]:
        return [
            UserInterestOut(
                category=item.category,
                label=_category_label(item.category),
                icon=_category_icon(item.category),
                weight=item.weight,
            )
            for item in interests
        ]

    def to_out(self, user: User) -> UserOut:
        return UserOut(
            id=user.id,
            created_at=user.created_at,
            last_login=user.last_login,
            profile=self._profile_out(user.profile),
            interests=self._interests_out(user.interests or []),
        )

    async def save_interests(self, user_id: uuid.UUID, categories: List[str]) -> UserOut:
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        normalized = []
        seen = set()
        for raw in categories:
            slug = raw.strip()
            if not slug or slug in seen:
                continue
            seen.add(slug)
            normalized.append(slug)

        await self.db.execute(
            delete(UserInterest).where(UserInterest.user_id == user_id)
        )

        for slug in normalized:
            self.db.add(UserInterest(user_id=user_id, category=slug))

        if user.profile is None:
            user.profile = UserProfile(user_id=user_id)
            self.db.add(user.profile)

        user.profile.onboarding_completed = True
        await self.db.commit()
        self.db.expire_all()
        refreshed = await self.get_by_id(user_id)
        if refreshed is None:
            raise ValueError("User not found")
        return self.to_out(refreshed)

    async def update_profile(
        self,
        user_id: uuid.UUID,
        *,
        display_name: Optional[str] = None,
        email_notifications: Optional[bool] = None,
        digest_frequency: Optional[str] = None,
    ) -> UserOut:
        user = await self.get_by_id(user_id)
        if user is None:
            raise ValueError("User not found")

        if user.profile is None:
            user.profile = UserProfile(user_id=user_id)
            self.db.add(user.profile)

        if display_name is not None:
            user.profile.display_name = display_name
        if email_notifications is not None:
            user.profile.email_notifications = email_notifications
        if digest_frequency is not None:
            user.profile.digest_frequency = digest_frequency

        await self.db.commit()
        self.db.expire_all()
        refreshed = await self.get_by_id(user_id)
        if refreshed is None:
            raise ValueError("User not found")
        return self.to_out(refreshed)
