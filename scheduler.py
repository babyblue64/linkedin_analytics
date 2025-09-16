# scheduler.py
import time
from database import get_db, Post, PostStatus
from sqlalchemy.orm import Session
from datetime import datetime, timezone

def find_and_publish_posts():
    db: Session = next(get_db())  # Get a database session outside of a FastAPI dependency
    try:
        current_time = datetime.now(timezone.utc)
        results = db.query(Post).filter(Post.status == PostStatus.SCHEDULED, Post.scheduled_at <= current_time).all()
        for post in results:
            print(f"Publishing post: {post.id} with title: {post.title}")
            # Simulate the LinkedIn API call
            # This would be an empty function
            post.status = PostStatus.PUBLISHED
            post.published_at = current_time
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error updating scheduled posts: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    while True:
        print(f"Scheduler running at {datetime.now(timezone.utc)}")
        find_and_publish_posts()
        time.sleep(60)  # Sleep for 60 seconds