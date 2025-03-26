from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.endpoints import router
from app.config import settings

app = FastAPI(
    title="iHubPT API",
    description="API for managing AI agents with HITL capabilities",
    version="1.0.0"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular development server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(
    router,
    prefix=settings.API_V1_PREFIX,
    tags=["agents"]
)

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to iHubPT API",
        "version": "1.0.0",
        "docs_url": "/docs",
        "redoc_url": "/redoc"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    ) 