from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CategoryOut(BaseModel):
    slug: str
    label: str
    icon: str
    item_count: int


class UserInterestOut(BaseModel):
    category: str
    label: str
    icon: str
    weight: float


class UserProfileOut(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    email_notifications: bool = True
    digest_frequency: str = "daily"
    onboarding_completed: bool = False


class UserOut(BaseModel):
    id: UUID
    created_at: datetime
    last_login: Optional[datetime] = None
    profile: UserProfileOut
    interests: List[UserInterestOut]


class InterestsUpdate(BaseModel):
    categories: List[str] = Field(..., min_length=0)


class ProfileUpdate(BaseModel):
    display_name: Optional[str] = None
    email_notifications: Optional[bool] = None
    digest_frequency: Optional[str] = None
