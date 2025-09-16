import enum
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
from sqlalchemy import ( 
    Column, 
    Integer, 
    String, 
    Enum, 
    DateTime, 
    ForeignKey, 
    Text, 
    create_engine, 
    func, 
    Boolean 
)
from datetime import datetime, timezone, timedelta
from sqlalchemy.ext.hybrid import hybrid_property
from dotenv import load_dotenv
import os
from sqlalchemy.dialects.postgresql import UUID
import uuid

# DATABASE MODELS

class UserRole(enum.Enum):
    USER = 'user'
    ADMIN = 'admin'

class PostStatus(enum.Enum):
    DRAFT = 'draft'
    SCHEDULED = 'scheduled'
    PUBLISHED = 'published'
    FAILED = 'failed'

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False, index=True)
    password_hash = Column(String(128), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.USER, index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=func.now())

    posts = relationship("Post", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user")

# In your database.py, fix the foreign key types:

class Post(Base):
    __tablename__ = 'posts'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False, index=True)  # Changed from Integer
    title = Column(String(200), nullable=False)
    content = Column(Text)
    status = Column(Enum(PostStatus), default=PostStatus.DRAFT, index=True)
    scheduled_at = Column(DateTime, index=True)
    published_at = Column(DateTime, index=True)
    created_at = Column(DateTime, default=datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=func.now())

    user = relationship("User", back_populates="posts")
    analytics = relationship("PostAnalytics", back_populates="post", uselist=False, cascade="all, delete-orphan")

class PostAnalytics(Base):
    __tablename__ = 'post_analytics'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    post_id = Column(UUID(as_uuid=True), ForeignKey('posts.id'), nullable=False, index=True, unique=True)  # Changed from Integer
    like_count = Column(Integer, default=0)
    praise_count = Column(Integer, default=0)
    empathy_count = Column(Integer, default=0)
    interest_count = Column(Integer, default=0)
    appreciation_count = Column(Integer, default=0)
    impressions_count = Column(Integer, default=0)
    shares_count = Column(Integer, default=0)
    comments_count = Column(Integer, default=0)
    updated_at = Column(DateTime, default=datetime.now(timezone.utc), onupdate=func.now())

    post = relationship("Post", back_populates="analytics")

    @hybrid_property
    def total_reactions(self):
        return (
            (self.like_count or 0) +
            (self.praise_count or 0) +
            (self.empathy_count or 0) +
            (self.interest_count or 0) +
            (self.appreciation_count or 0)
        )

    @hybrid_property
    def total_engagements(self):
        return (
            self.total_reactions +
            (self.shares_count or 0) +
            (self.comments_count or 0)
        )

class RefreshToken(Base):
    __tablename__ = 'refresh_tokens'

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    jti = Column(String, unique=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'))  # Changed from Integer
    is_active = Column(Boolean, default=True)
    expires_at = Column(DateTime, default=datetime.now(timezone.utc) + timedelta(days=7))
    created_at = Column(DateTime, default=datetime.now(timezone.utc))

    user = relationship("User", back_populates="refresh_tokens")
    
# DEPENDENCY INJECTION FUNCTION

load_dotenv()

DB_URL = os.getenv('DB_URL')

engine = create_engine(DB_URL)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()