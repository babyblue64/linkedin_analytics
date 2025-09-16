from pydantic import BaseModel, EmailStr
from datetime import datetime
from enum import Enum
from typing import List

# AUTH MODELS

class UserRegister(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class RefreshTokenRequest(BaseModel):
    refresh_token: str

# POST MODELS

class PostStatus(str, Enum):
    DRAFT = 'draft'
    SCHEDULED = 'scheduled' 
    PUBLISHED = 'published'
    FAILED = 'failed'

class PostCreate(BaseModel):
    title: str
    content: str | None = None
    scheduled_at: datetime | None = None
    publish_now: bool = False

class PostUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
    status: PostStatus | None = None
    scheduled_at: datetime | None

class PostResponse(BaseModel):
    id: str
    title: str
    content: str | None
    status: str
    scheduled_at: datetime | None
    published_at: datetime | None
    created_at: datetime
    updated_at: datetime
    user_id: str

    class Config:
        from_attributes = True

class PostListResponse(BaseModel):
    posts: list[PostResponse]
    total: int
    page: int
    limit: int

# ANALYTICS MODELS

class ReactionsUpdate(BaseModel):
    like_count: int | None = None
    praise_count: int | None = None
    empathy_count: int | None = None
    interest_count: int | None = None
    appreciation_count: int | None = None
    impressions_count: int | None = None
    shares_count: int | None = None
    comments_count: int | None = None

class PostAnalyticsResponse(BaseModel):
    id: str
    post_id: str
    like_count: int
    praise_count: int
    empathy_count: int
    interest_count: int
    appreciation_count: int
    impressions_count: int
    shares_count: int
    comments_count: int
    total_reactions: int
    total_engagements: int
    updated_at: datetime

    class Config:
        from_attributes = True

class PostWithAnalytics(BaseModel):
    # Post details
    id: str
    title: str
    content: str | None
    status: str
    published_at: datetime | None
    created_at: datetime
    user_id: str
    
    # Analytics data
    analytics: PostAnalyticsResponse | None

    class Config:
        from_attributes = True

class TopPostsResponse(BaseModel):
    posts: List[PostWithAnalytics]
    metric: str  # "engagement", "reactions", "impressions"
    limit: int

class AnalyticsGraphData(BaseModel):
    date: str  # YYYY-MM-DD format
    reactions: int
    engagements: int
    impressions: int
    shares: int
    comments: int

class PostAnalyticsGraph(BaseModel):
    post_id: str
    post_title: str
    data: List[AnalyticsGraphData]