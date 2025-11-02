"""
FastAPI main application.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os
from pathlib import Path

from .config import settings, get_cors_origins
from .routers import health, admin, search

# Create FastAPI app
app = FastAPI(
    title="AI Web Image Service",
    description="AI-powered vector-searchable image library for cottage food businesses",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, tags=["Health"])
app.include_router(search.router, prefix=settings.api_v1_prefix, tags=["Search"])
app.include_router(admin.router, prefix="/api/admin", tags=["Admin"])

# Serve images with proper CORS headers
storage_path = Path(settings.storage_path)

@app.get("/storage/{file_path:path}")
async def serve_storage(file_path: str):
    """
    Serve storage files with proper CORS headers.
    This endpoint serves images from the storage directory.
    """
    file_location = storage_path / file_path

    # Security check: ensure file is within storage directory
    try:
        file_location = file_location.resolve()
        storage_path_resolved = storage_path.resolve()
        if not str(file_location).startswith(str(storage_path_resolved)):
            raise HTTPException(status_code=403, detail="Access denied")
    except Exception:
        raise HTTPException(status_code=404, detail="File not found")

    if not file_location.exists() or not file_location.is_file():
        raise HTTPException(status_code=404, detail="File not found")

    return FileResponse(
        file_location,
        media_type="image/jpeg",
        headers={
            "Cache-Control": "public, max-age=31536000",  # Cache for 1 year
            "Access-Control-Allow-Origin": "*",  # Allow all origins for images
        }
    )


@app.on_event("startup")
async def startup_event():
    """Run on application startup."""
    print(f"Starting AIWebImageService in {settings.env} mode")
    print(f"Storage path: {settings.storage_path}")


@app.on_event("shutdown")
async def shutdown_event():
    """Run on application shutdown."""
    print("Shutting down AIWebImageService")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "AI Web Image Service",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs"
    }
