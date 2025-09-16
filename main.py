from fastapi import FastAPI
from routes import auth, posts, analytics

app = FastAPI(
    title="LinkedIn Analytics Backend",
    description="A simplified LinkedIn analytics platform backend",
    version="1.0.0"
)

@app.get('/health')
def health_check():
    return {"detail": "working"}

app.include_router(auth.router, tags=["Authentication"])
app.include_router(posts.router, prefix="/posts", tags=["Posts"])
app.include_router(analytics.router, prefix="/analytics", tags=["Analytics"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, reload=True, port=8000)