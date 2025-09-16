from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, func
from database import get_db, User, UserRole, Post, PostStatus, PostAnalytics
from pydantic_models import (
    PostAnalyticsResponse,
    ReactionsUpdate,
    TopPostsResponse,
    PostAnalyticsGraph,
    AnalyticsGraphData
)
from utils import get_current_user
from typing import Literal
from datetime import datetime, timedelta
import uuid

router = APIRouter()

@router.get('/posts/{post_id}', response_model=PostAnalyticsResponse)
def get_post_analytics(
    post_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    post = db.query(Post).filter(Post.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if current_user.role != UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this post's analytics")
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_uuid).first()
    if not analytics:
        analytics = PostAnalytics(post_id=post_uuid)
        db.add(analytics)
        db.commit()
        db.refresh(analytics)
    
    return analytics

@router.put('/posts/{post_id}', response_model=PostAnalyticsResponse)
def update_post_analytics(
    post_id: str,
    analytics_data: ReactionsUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    post = db.query(Post).filter(Post.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    # Check authorization - only admins or post owners can update analytics
    if current_user.role != UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to update this post's analytics")
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_uuid).first()
    if not analytics:
        analytics = PostAnalytics(post_id=post_uuid)
        db.add(analytics)
        db.flush()  # Get the ID without committing
    
    update_data = analytics_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:  # Only update non-None values
            setattr(analytics, field, value)
    
    db.commit()
    db.refresh(analytics)
    
    return analytics

@router.get('/posts/top', response_model=TopPostsResponse)
def get_top_posts(
    metric: Literal["engagement", "reactions", "impressions"] = Query("engagement"),
    limit: int = Query(5, ge=1, le=50),
    user_id: str | None = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    query = db.query(Post).join(
        PostAnalytics, 
        Post.id == PostAnalytics.post_id,
        isouter=True  # LEFT JOIN to include posts without analytics
    ).options(joinedload(Post.analytics))
    
    # Role-based filtering
    if current_user.role != UserRole.ADMIN:
        query = query.filter(Post.user_id == current_user.id)
    elif user_id:
        try:
            user_uuid = uuid.UUID(user_id)
            query = query.filter(Post.user_id == user_uuid)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid user_id format")
    
    query = query.filter(Post.status == PostStatus.PUBLISHED)
    
    if metric == "engagement":
        query = query.order_by(desc(
            PostAnalytics.like_count + 
            PostAnalytics.praise_count + 
            PostAnalytics.empathy_count + 
            PostAnalytics.interest_count + 
            PostAnalytics.appreciation_count + 
            PostAnalytics.shares_count + 
            PostAnalytics.comments_count
        ))
    elif metric == "reactions":
        query = query.order_by(desc(
            PostAnalytics.like_count + 
            PostAnalytics.praise_count + 
            PostAnalytics.empathy_count + 
            PostAnalytics.interest_count + 
            PostAnalytics.appreciation_count
        ))
    elif metric == "impressions":
        query = query.order_by(desc(PostAnalytics.impressions_count))
    
    posts = query.limit(limit).all()
    
    return TopPostsResponse(
        posts=posts,
        metric=metric,
        limit=limit
    )

@router.get('/posts/{post_id}/graph', response_model=PostAnalyticsGraph)
def get_post_analytics_graph(
    post_id: str,
    days: int = Query(30, ge=1, le=365),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    try:
        post_uuid = uuid.UUID(post_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid post ID format")
    
    post = db.query(Post).filter(Post.id == post_uuid).first()
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")
    
    if current_user.role != UserRole.ADMIN and post.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized to view this post's analytics")
    
    analytics = db.query(PostAnalytics).filter(PostAnalytics.post_id == post_uuid).first()
    
    # For simplicity, we'll simulate daily breakdown data
    graph_data = []
    
    if analytics:

        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
            
            factor = (i + 1) / days
            
            graph_data.append(AnalyticsGraphData(
                date=date,
                reactions=int(analytics.total_reactions * factor),
                engagements=int(analytics.total_engagements * factor),
                impressions=int(analytics.impressions_count * factor),
                shares=int(analytics.shares_count * factor),
                comments=int(analytics.comments_count * factor)
            ))
    else:
        # Return zeros if no analytics exist
        for i in range(days):
            date = (datetime.now() - timedelta(days=days-i-1)).strftime("%Y-%m-%d")
            graph_data.append(AnalyticsGraphData(
                date=date,
                reactions=0,
                engagements=0,
                impressions=0,
                shares=0,
                comments=0
            ))
    
    return PostAnalyticsGraph(
        post_id=post_id,
        post_title=post.title,
        data=graph_data
    )

@router.get('/summary')
def get_user_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):

    posts_query = db.query(Post).filter(Post.user_id == current_user.id)
    
    if current_user.role == UserRole.ADMIN:
        # Admin can see all posts summary
        posts_query = db.query(Post)
    
    # Get summary statistics
    total_posts = posts_query.count()
    published_posts = posts_query.filter(Post.status == PostStatus.PUBLISHED).count()
    scheduled_posts = posts_query.filter(Post.status == PostStatus.SCHEDULED).count()
    draft_posts = posts_query.filter(Post.status == PostStatus.DRAFT).count()
    
    # Get analytics totals
    analytics_query = db.query(PostAnalytics).join(Post)
    
    if current_user.role != UserRole.ADMIN:
        analytics_query = analytics_query.filter(Post.user_id == current_user.id)
    
    totals = analytics_query.with_entities(
        func.sum(PostAnalytics.like_count).label('total_likes'),
        func.sum(PostAnalytics.praise_count).label('total_praise'),
        func.sum(PostAnalytics.empathy_count).label('total_empathy'),
        func.sum(PostAnalytics.interest_count).label('total_interest'),
        func.sum(PostAnalytics.appreciation_count).label('total_appreciation'),
        func.sum(PostAnalytics.impressions_count).label('total_impressions'),
        func.sum(PostAnalytics.shares_count).label('total_shares'),
        func.sum(PostAnalytics.comments_count).label('total_comments'),
    ).first()
    
    total_reactions = (
        (totals.total_likes or 0) +
        (totals.total_praise or 0) +
        (totals.total_empathy or 0) +
        (totals.total_interest or 0) +
        (totals.total_appreciation or 0)
    )
    
    total_engagements = total_reactions + (totals.total_shares or 0) + (totals.total_comments or 0)
    
    return {
        "user_id": str(current_user.id),
        "user_name": current_user.name,
        "posts_summary": {
            "total_posts": total_posts,
            "published_posts": published_posts,
            "scheduled_posts": scheduled_posts,
            "draft_posts": draft_posts
        },
        "engagement_summary": {
            "total_reactions": total_reactions,
            "total_engagements": total_engagements,
            "total_impressions": totals.total_impressions or 0,
            "total_shares": totals.total_shares or 0,
            "total_comments": totals.total_comments or 0,
            "breakdown": {
                "likes": totals.total_likes or 0,
                "praise": totals.total_praise or 0,
                "empathy": totals.total_empathy or 0,
                "interest": totals.total_interest or 0,
                "appreciation": totals.total_appreciation or 0
            }
        }
    }