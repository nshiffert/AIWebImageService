"""
Pydantic models for API request/response validation.
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from uuid import UUID


# Request Models
class SearchRequest(BaseModel):
    """Search request model."""
    query: str = Field(..., description="Search query text")
    size: str = Field(default="product_card", description="Image size preset")
    limit: int = Field(default=10, ge=1, le=50, description="Maximum number of results")
    min_score: float = Field(default=0.7, ge=0.0, le=1.0, description="Minimum similarity score")


class GenerateImageRequest(BaseModel):
    """Single image generation request."""
    prompt: str = Field(..., description="Image generation prompt")
    style: str = Field(default="product_photography", description="Image style")


class GenerateBatchRequest(BaseModel):
    """Batch image generation request."""
    prompts: List[str] = Field(..., description="List of prompts to generate")
    style: str = Field(default="product_photography", description="Image style")
    count_per_prompt: int = Field(default=1, ge=1, le=5, description="Images per prompt")


class ApproveImageRequest(BaseModel):
    """Image approval request."""
    override_tags: Optional[List[str]] = Field(default=None, description="Optional tag overrides")


# Response Models
class ImageVariantResponse(BaseModel):
    """Image variant information."""
    size_preset: str
    width: int
    height: int
    storage_path: str
    file_size_bytes: Optional[int] = None


class ImageTagResponse(BaseModel):
    """Image tag information."""
    tag: str
    confidence: float
    source: str


class ImageColorResponse(BaseModel):
    """Image color information."""
    color_hex: str
    percentage: float
    is_dominant: bool


class ImageResponse(BaseModel):
    """Complete image information."""
    id: UUID
    prompt: str
    style: str
    status: str
    description: Optional[str] = None
    tags: List[ImageTagResponse] = []
    colors: List[ImageColorResponse] = []
    variants: List[ImageVariantResponse] = []
    created_at: datetime
    approved_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SearchResultItem(BaseModel):
    """Single search result item."""
    id: UUID
    storage_path: str
    score: float
    tags: List[str]
    description: Optional[str] = None
    dominant_color: Optional[str] = None


class SearchResponse(BaseModel):
    """Search results response."""
    results: List[SearchResultItem]
    total: int
    query_time_ms: float


class GenerationStatusResponse(BaseModel):
    """Image generation status."""
    image_id: Optional[UUID] = None
    status: str
    message: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    database: str
    openai: str
    timestamp: datetime


class StatsResponse(BaseModel):
    """System statistics."""
    total_images: int
    approved_images: int
    pending_review: int
    total_tags: int
    storage_used_mb: float


# Job Tracking Models
class GenerationTaskResponse(BaseModel):
    """Individual generation task within a job."""
    id: UUID
    job_id: UUID
    prompt: str
    style: str
    status: str
    image_id: Optional[UUID] = None
    error_message: Optional[str] = None
    retry_count: int
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class GenerationJobResponse(BaseModel):
    """Batch generation job with tasks."""
    id: UUID
    status: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    created_at: datetime
    completed_at: Optional[datetime] = None
    updated_at: datetime
    tasks: List[GenerationTaskResponse] = []

    class Config:
        from_attributes = True


class JobStatusResponse(BaseModel):
    """Lightweight job status for polling."""
    id: UUID
    status: str
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percentage: float
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True
