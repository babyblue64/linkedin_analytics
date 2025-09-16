from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from database import get_db, User, UserRole, Post, PostStatus
from pydantic_models import (
    PostCreate, 
    PostUpdate, 
    PostResponse,
    PostListResponse
)
from utils import get_current_user, create_post_analytics
import uuid
from datetime import datetime, timezone

router = APIRouter()

@router.post('/', response_model=PostResponse)
def create_post(
    post_data: PostCreate, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    post_status = PostStatus.DRAFT
    published_at = None
    
    # Handle immediate publish
    if post_data.publish_now:
        post_status = PostStatus.PUBLISHED
        published_at = datetime.now(timezone.utc)
        if post_data.scheduled_at:
             raise HTTPException(status_code=400, detail="Cannot schedule and publish immediately at the same time")
    
    # Handle scheduling for a future time
    elif post_data.scheduled_at:
        if post_data.scheduled_at <= datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Scheduled time cannot be in the past")
        post_status = PostStatus.SCHEDULED

    new_post = Post(
        user_id=current_user.id,
        title=post_data.title,
        content=post_data.content,
        status=post_status,
        scheduled_at=post_data.scheduled_at if post_status == PostStatus.SCHEDULED else None,
        published_at=published_at
    )
    
    db.add(new_post)
    db.commit()
    db.refresh(new_post)
    
    create_post_analytics(str(new_post.id), db)
    
    return new_post

@router.get('/', response_model=PostListResponse)
def get_posts(
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    status: PostStatus | None = None,
    user_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Base query
    query = db.query(Post)
    
    # Role-based filtering
    if current_user.role != UserRole.ADMIN:
        # Regular users can only see their own posts
        query = query.filter(Post.user_id == current_user.id)
    elif user_id:
        # Admin can filter by specific user_id
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.filter(Post.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    # Status filter
    if status:
        query = query.filter(Post.status == status)
    
    # Get total count
    total = query.count()
    
    # Apply pagination
    offset = (page - 1) * limit
    posts = query.offset(offset).limit(limit).all()
    
    return PostListResponse(
        posts=posts,
        total=total,
        page=page,
        limit=limit
    )

@router.get('/{post_id}', response_model=PostResponse)
def get_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate UUID format
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    # Get the post
    post = db.query(Post).filter(Post.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization
    if current_user.role != UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this post")
    
    return post

@router.put('/{post_id}', response_model=PostResponse)
def update_post(                                                # you are here
    post_id: str,
    post_data: PostUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate UUID format
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    # Get the post
    post = db.query(Post).filter(Post.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization
    if current_user.role != UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post")
    
    # Update fields
    update_data = post_data.model_dump(exclude_unset=True)

    if 'scheduled_at' in update_data:
        scheduled_at = update_data['scheduled_at']
        if scheduled_at and scheduled_at < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="Scheduled time cannot be in the past")
        
        post.scheduled_at = scheduled_at
        post.status = PostStatus.SCHEDULED

    for field, value in update_data.items():
        setattr(post, field, value)
    
    db.commit()
    db.refresh(post)
    
    return post

@router.delete('/{post_id}')
def delete_post(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Validate UUID format
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    # Get the post
    post = db.query(Post).filter(Post.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization
    if current_user.role != UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this post")
    
    db.delete(post)
    db.commit()
    
    return {"detail": "Post deleted successfully"}