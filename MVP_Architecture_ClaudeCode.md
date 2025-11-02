# AIWebImageService MVP — Architecture Document
## For Claude Code Implementation

## 1. Executive Summary

AIWebImageService is a vector-searchable stock image library with AI generation capabilities, designed specifically for the cottage food business website builder. It provides a read-only API for finding the best matching images based on text queries, while image generation and management is handled through an admin panel.

## 2. Project Structure

```
aiwebimageservice/
├── backend/
│   ├── api/                 # FastAPI application
│   │   ├── main.py          # App entry point
│   │   ├── routers/         # API endpoints
│   │   │   ├── search.py    # Search endpoint
│   │   │   ├── admin.py     # Admin API endpoints
│   │   │   └── health.py    # Health check
│   │   ├── services/        # Business logic
│   │   │   ├── generator.py # Image generation
│   │   │   ├── tagger.py    # Auto-tagging
│   │   │   ├── storage.py   # S3 operations
│   │   │   └── embeddings.py# Vector operations
│   │   ├── models/          # Pydantic models
│   │   │   ├── image.py
│   │   │   └── search.py
│   │   └── db/              # Database
│   │       ├── database.py  # Connection
│   │       ├── models.py    # SQLAlchemy models
│   │       └── migrations/  # Alembic migrations
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── pages/           # React pages
│   │   │   ├── Dashboard.tsx
│   │   │   ├── Generate.tsx
│   │   │   ├── Review.tsx
│   │   │   └── Library.tsx
│   │   ├── components/      # Reusable components
│   │   │   ├── ImageGrid.tsx
│   │   │   ├── TagDisplay.tsx
│   │   │   ├── ColorPicker.tsx
│   │   │   └── SearchTest.tsx
│   │   ├── services/        # API clients
│   │   │   ├── api.ts
│   │   │   └── auth.ts
│   │   └── App.tsx
│   ├── package.json
│   └── tsconfig.json
├── scripts/
│   ├── setup_db.py          # Database initialization
│   ├── seed_data.py         # Initial data seeding
│   └── test_search.py       # Search testing
├── docker-compose.yml       # Local development
├── Dockerfile.api
├── Dockerfile.frontend
└── README.md
```

## 3. Tech Stack Decisions

### Backend (Python/FastAPI)
```python
# requirements.txt
fastapi==0.104.1
uvicorn==0.24.0
supabase==2.3.0
pydantic==2.5.0
python-multipart==0.0.6
openai==1.3.7
pillow==10.1.0
python-jose[cryptography]==3.3.0
python-dotenv==1.0.0
httpx==0.25.1
google-cloud-secret-manager==2.16.4
google-cloud-monitoring==2.16.0
google-cloud-storage==2.13.0
```

### Frontend (React/TypeScript)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-router-dom": "^6.20.0",
    "@supabase/supabase-js": "^2.39.0",
    "tailwindcss": "^3.3.6",
    "@tanstack/react-query": "^5.8.4",
    "react-hook-form": "^7.48.2",
    "lucide-react": "^0.294.0",
    "react-color": "^2.19.3",
    "react-dropzone": "^14.2.3",
    "sonner": "^1.2.4"
  }
}
```

### Infrastructure
- **Database**: Supabase PostgreSQL (pgvector pre-enabled)
- **Storage**: Supabase Storage (with CDN)
- **Authentication**: Supabase Auth
- **Backend Hosting**: Google Cloud Run
- **Frontend Hosting**: Google Cloud Run or Firebase Hosting
- **CDN**: Google Cloud CDN + Supabase CDN
- **Secrets**: Google Secret Manager
- **Container**: Docker for Cloud Run deployment

## 4. Database Schema

```sql
-- Supabase already has pgvector enabled!
-- migrations/001_initial_schema.sql

-- Note: uuid-ossp is pre-enabled in Supabase
-- Note: vector extension is pre-enabled in Supabase

-- Core image table
CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt TEXT NOT NULL,
    style VARCHAR(50) DEFAULT 'product_photography',
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'tagging', 'ready', 'approved', 'rejected')),
    auto_tagged BOOLEAN DEFAULT FALSE,
    tagging_confidence FLOAT,
    generation_cost DECIMAL(10,4),
    tagging_cost DECIMAL(10,4),
    error_message TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES auth.users(id),  -- Supabase auth integration
    approved_at TIMESTAMP WITH TIME ZONE,
    approved_by UUID REFERENCES auth.users(id)
);

-- Image size variants
CREATE TABLE image_variants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    size_preset VARCHAR(20) NOT NULL,
    width INTEGER NOT NULL,
    height INTEGER NOT NULL,
    storage_path TEXT NOT NULL,  -- Supabase storage path
    public_url TEXT NOT NULL,    -- Supabase public URL
    file_size_bytes INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(image_id, size_preset)
);

-- Tags with source tracking
CREATE TABLE image_tags (
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    tag VARCHAR(50) NOT NULL,
    confidence FLOAT DEFAULT 1.0,
    source VARCHAR(20) DEFAULT 'auto' CHECK (source IN ('auto', 'manual', 'template')),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    PRIMARY KEY(image_id, tag)
);

-- AI-generated descriptions
CREATE TABLE image_descriptions (
    image_id UUID PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    description TEXT NOT NULL,
    vision_analysis JSONB,
    model_version VARCHAR(50),
    generated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Color analysis
CREATE TABLE image_colors (
    image_id UUID NOT NULL REFERENCES images(id) ON DELETE CASCADE,
    color_hex CHAR(7) NOT NULL,
    percentage FLOAT NOT NULL CHECK (percentage >= 0 AND percentage <= 100),
    is_dominant BOOLEAN DEFAULT FALSE,
    PRIMARY KEY(image_id, color_hex)
);

-- Vector embeddings for search
CREATE TABLE image_embeddings (
    image_id UUID PRIMARY KEY REFERENCES images(id) ON DELETE CASCADE,
    embedding vector(1536) NOT NULL,
    embedding_source TEXT,
    model_version VARCHAR(50) DEFAULT 'text-embedding-ada-002',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Async generation jobs tracking
CREATE TABLE generation_jobs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    provider VARCHAR(20) NOT NULL,
    provider_job_id VARCHAR(255),
    status VARCHAR(20) DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    progress INTEGER DEFAULT 0,
    image_id UUID REFERENCES images(id),
    prompt TEXT NOT NULL,
    style VARCHAR(50),
    callback_url TEXT,
    webhook_data JSONB,
    error_message TEXT,
    estimated_time INTEGER,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    completed_at TIMESTAMP WITH TIME ZONE,
    created_by UUID REFERENCES auth.users(id)
);

CREATE INDEX idx_generation_jobs_status ON generation_jobs(status);
CREATE INDEX idx_generation_jobs_provider ON generation_jobs(provider, provider_job_id);

-- API keys for search (using Supabase RLS)
CREATE TABLE api_keys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100),
    key_hash TEXT UNIQUE NOT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    rate_limit INTEGER DEFAULT 100,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE,
    owner_id UUID REFERENCES auth.users(id)
);

-- Indexes for performance
CREATE INDEX idx_images_status ON images(status);
CREATE INDEX idx_images_created ON images(created_at DESC);
CREATE INDEX idx_images_approved ON images(approved_at DESC) WHERE status = 'approved';
CREATE INDEX idx_tags_tag ON image_tags(tag);
CREATE INDEX idx_embeddings_vector ON image_embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);
CREATE INDEX idx_api_keys_hash ON api_keys(key_hash);

-- Enable Row Level Security
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_tags ENABLE ROW LEVEL SECURITY;
ALTER TABLE api_keys ENABLE ROW LEVEL SECURITY;

-- RLS Policies
CREATE POLICY "Service role has full access" ON images
    FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Approved images are public" ON images
    FOR SELECT USING (status = 'approved');

CREATE POLICY "Public can view approved image variants" ON image_variants
    FOR SELECT USING (
        EXISTS (
            SELECT 1 FROM images 
            WHERE images.id = image_variants.image_id 
            AND images.status = 'approved'
        )
    );

-- Supabase Storage bucket setup (run in Supabase Dashboard SQL Editor)
INSERT INTO storage.buckets (id, name, public) 
VALUES ('images', 'images', true);

-- RPC function for vector search
CREATE OR REPLACE FUNCTION search_similar_images(
    query_embedding vector(1536),
    match_threshold float DEFAULT 0.7,
    match_count int DEFAULT 10,
    size_preset text DEFAULT 'product_card'
)
RETURNS TABLE (
    id uuid,
    url text,
    score float,
    tags text[],
    description text,
    dominant_color text,
    all_sizes jsonb
)
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    SELECT 
        i.id,
        iv.public_url as url,
        1 - (ie.embedding <=> query_embedding) as score,
        array_agg(DISTINCT it.tag) as tags,
        id.description,
        (SELECT ic.color_hex FROM image_colors ic 
         WHERE ic.image_id = i.id AND ic.is_dominant = true 
         LIMIT 1) as dominant_color,
        (SELECT jsonb_object_agg(v.size_preset, v.public_url)
         FROM image_variants v 
         WHERE v.image_id = i.id) as all_sizes
    FROM images i
    JOIN image_embeddings ie ON i.id = ie.image_id
    JOIN image_variants iv ON i.id = iv.image_id AND iv.size_preset = size_preset
    LEFT JOIN image_tags it ON i.id = it.image_id
    LEFT JOIN image_descriptions id ON i.id = id.image_id
    WHERE 
        i.status = 'approved'
        AND 1 - (ie.embedding <=> query_embedding) > match_threshold
    GROUP BY i.id, iv.public_url, id.description, ie.embedding
    ORDER BY score DESC
    LIMIT match_count;
END;
$$;
```

## 5. API Specifications

### Search API

```python
# backend/api/routers/search.py

from fastapi import APIRouter, Depends, HTTPException, Header
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/api/v1")

class SearchRequest(BaseModel):
    query: str
    size: str = "product_card"  # thumbnail, product_card, full_product, hero_image, full_res
    limit: int = 10
    min_score: float = 0.7

class ImageResult(BaseModel):
    id: str
    url: str
    score: float
    tags: List[str]
    description: str
    dominant_color: Optional[str]
    sizes: dict[str, str]

class SearchResponse(BaseModel):
    results: List[ImageResult]
    total: int
    query_time_ms: int

@router.post("/search", response_model=SearchResponse)
async def search_images(
    request: SearchRequest,
    api_key: str = Header(..., alias="X-API-Key"),
    db = Depends(get_db)
):
    """
    Vector search for images based on text query.
    Returns matched images with URLs for requested size.
    """
    # Implementation here
```

### Admin API

```python
# backend/api/routers/admin.py

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from enum import Enum

router = APIRouter(prefix="/api/admin")

class ImageProvider(str, Enum):
    OPENAI = "openai"
    LEONARDO = "leonardo"
    RUNWARE = "runware"

class GenerateBatchRequest(BaseModel):
    prompts: List[str]
    colors: List[str]  # Hex colors
    style: str = "product_photography"
    count_per_prompt: int = 1
    provider: ImageProvider = ImageProvider.OPENAI  # Allow provider selection

class GenerationStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    provider: str
    is_async: bool
    progress: int = 0
    total: int
    completed: List[str]
    failed: List[dict]
    estimated_time: Optional[int] = None

@router.post("/generate/batch")
async def generate_batch(
    request: GenerateBatchRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_admin)
):
    """
    Start batch image generation with specified prompts and colors.
    Handles both sync and async providers.
    """
    # Initialize generator with specified provider
    generator = ImageGenerator(provider=request.provider)
    
    # Check if provider is async
    if generator.provider.is_async():
        # Queue async generation jobs
        job_id = str(uuid4())
        background_tasks.add_task(
            process_async_batch,
            job_id,
            request,
            generator
        )
        return {
            "job_id": job_id,
            "status": "pending",
            "is_async": True,
            "provider": request.provider,
            "message": "Batch generation started. Check status endpoint for progress."
        }
    else:
        # Process sync generation immediately
        results = await process_sync_batch(request, generator)
        return {
            "status": "completed",
            "is_async": False,
            "provider": request.provider,
            "results": results
        }

@router.get("/generate/status/{job_id}")
async def get_generation_status(
    job_id: str,
    current_user = Depends(get_current_admin)
):
    """Check status of batch generation job (for async providers)."""
    generator = ImageGenerator()
    status = await generator.check_generation_status(job_id)
    return status

@router.post("/webhooks/{provider}")
async def handle_provider_webhook(
    provider: str,
    data: Dict[str, Any],
    background_tasks: BackgroundTasks
):
    """
    Handle webhooks from async image generation providers.
    Each provider has different webhook format.
    """
    if provider not in ["leonardo", "runware"]:
        raise HTTPException(status_code=400, detail="Unknown provider")
    
    generator = ImageGenerator(provider=provider)
    background_tasks.add_task(
        generator.handle_webhook,
        provider,
        data
    )
    
    return {"status": "received"}

@router.post("/images/{image_id}/approve")
async def approve_image(
    image_id: str,
    override_tags: Optional[List[str]] = None,
    current_user = Depends(get_current_admin)
):
    """Approve image for search index with optional tag override."""
    # Implementation
    
@router.get("/images/review")
async def list_review_queue(
    limit: int = 20,
    current_user = Depends(get_current_admin)
):
    """List images pending review with auto-generated tags."""
    # Implementation

@router.get("/providers")
async def list_available_providers(
    current_user = Depends(get_current_admin)
):
    """List available image generation providers and their status."""
    providers = {
        "openai": {
            "name": "OpenAI DALL-E 3",
            "is_async": False,
            "available": bool(config.openai_api_key),
            "cost_per_image": 0.04,
            "features": ["high_quality", "synchronous", "reliable"]
        },
        "leonardo": {
            "name": "Leonardo.ai",
            "is_async": True,
            "available": bool(config.leonardo_api_key),
            "cost_per_image": 0.002,
            "features": ["low_cost", "webhooks", "multiple_models"]
        },
        "runware": {
            "name": "Runware",
            "is_async": True,
            "available": bool(config.runware_api_key),
            "cost_per_image": 0.003,
            "features": ["fast", "scalable", "good_quality"]
        }
    }
    return providers
```

## 6. Core Services Implementation

### Supabase Client Configuration

```python
# backend/api/config.py

from supabase import create_client, Client
from google.cloud import secretmanager
import os
from typing import Optional

class Config:
    def __init__(self):
        self.secret_client = secretmanager.SecretManagerServiceClient()
        self.project_id = os.getenv("GCP_PROJECT_ID")
        
    def get_secret(self, secret_id: str) -> str:
        """Fetch secret from Google Secret Manager."""
        name = f"projects/{self.project_id}/secrets/{secret_id}/versions/latest"
        response = self.secret_client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    
    @property
    def supabase_client(self) -> Client:
        """Initialize Supabase client with service role key."""
        return create_client(
            os.getenv("SUPABASE_URL"),
            self.get_secret("supabase-service-key")
        )
    
    @property
    def openai_api_key(self) -> str:
        return self.get_secret("openai-api-key")

config = Config()
supabase = config.supabase_client
```

### Image Generation Service with Provider Interface

```python
# backend/api/services/providers/base.py

from abc import ABC, abstractmethod
from typing import Dict, Optional, Any, Callable
from enum import Enum

class GenerationStatus(Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ImageProviderBase(ABC):
    """Base interface for image generation providers."""
    
    @abstractmethod
    async def generate(
        self, 
        prompt: str, 
        width: int = 1024,
        height: int = 1024,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate an image from prompt.
        Returns either:
        - Synchronous: {"status": "completed", "image_url": "...", "image_bytes": b"..."}
        - Asynchronous: {"status": "pending", "job_id": "...", "check_url": "..."}
        """
        pass
    
    @abstractmethod
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of async generation job."""
        pass
    
    @abstractmethod
    def is_async(self) -> bool:
        """Return True if provider requires async polling/callbacks."""
        pass
    
    @abstractmethod
    def get_cost_estimate(self, width: int, height: int) -> float:
        """Estimate cost for generation."""
        pass

# backend/api/services/providers/openai_provider.py

import openai
import httpx
from typing import Dict, Any, Optional

class OpenAIProvider(ImageProviderBase):
    """OpenAI DALL-E 3 provider (synchronous)."""
    
    def __init__(self, api_key: str):
        self.client = openai.AsyncClient(api_key=api_key)
        
    async def generate(
        self, 
        prompt: str, 
        width: int = 1024,
        height: int = 1024,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        # DALL-E 3 only supports specific sizes
        size = f"{width}x{height}"
        if size not in ["1024x1024", "1024x1792", "1792x1024"]:
            size = "1024x1024"
        
        response = await self.client.images.generate(
            model="dall-e-3",
            prompt=prompt,
            size=size,
            quality="hd",
            n=1
        )
        
        image_url = response.data[0].url
        
        # Download image
        async with httpx.AsyncClient() as client:
            img_response = await client.get(image_url)
            image_bytes = img_response.content
        
        return {
            "status": "completed",
            "image_url": image_url,
            "image_bytes": image_bytes,
            "provider": "openai",
            "model": "dall-e-3"
        }
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        # OpenAI is synchronous, no status check needed
        return {"status": "completed"}
    
    def is_async(self) -> bool:
        return False
    
    def get_cost_estimate(self, width: int, height: int) -> float:
        # DALL-E 3 pricing
        if width > 1024 or height > 1024:
            return 0.08  # HD quality, larger size
        return 0.04  # HD quality, standard size

# backend/api/services/providers/leonardo_provider.py

import httpx
from typing import Dict, Any, Optional

class LeonardoProvider(ImageProviderBase):
    """Leonardo.ai provider (asynchronous with webhooks)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://cloud.leonardo.ai/api/rest/v1"
        
    async def generate(
        self, 
        prompt: str, 
        width: int = 1024,
        height: int = 1024,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/generations",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "num_images": 1,
                    "modelId": "6bef9f1b-29cb-40c7-b9df-32b51c1f67d3",  # Leonardo Diffusion XL
                    "webhookUrl": callback_url
                }
            )
            
            data = response.json()
            
            return {
                "status": "pending",
                "job_id": data["sdGenerationJob"]["generationId"],
                "check_url": f"{self.base_url}/generations/{data['sdGenerationJob']['generationId']}",
                "provider": "leonardo",
                "estimated_time": 30
            }
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/generations/{job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            data = response.json()
            generation = data["generations_by_pk"]
            
            if generation["status"] == "COMPLETE":
                image_url = generation["generated_images"][0]["url"]
                
                # Download image
                img_response = await client.get(image_url)
                
                return {
                    "status": "completed",
                    "image_url": image_url,
                    "image_bytes": img_response.content
                }
            elif generation["status"] == "FAILED":
                return {
                    "status": "failed",
                    "error": "Generation failed"
                }
            else:
                return {
                    "status": "processing",
                    "progress": generation.get("progress", 0)
                }
    
    def is_async(self) -> bool:
        return True
    
    def get_cost_estimate(self, width: int, height: int) -> float:
        # Leonardo pricing (approximate)
        pixels = width * height
        base_cost = 0.002  # Per image base
        if pixels > 1024 * 1024:
            return base_cost * 2
        return base_cost

# backend/api/services/providers/runware_provider.py

import httpx
from typing import Dict, Any, Optional
import asyncio

class RunwareProvider(ImageProviderBase):
    """Runware API provider (async with polling)."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.runware.ai/v1"
        
    async def generate(
        self, 
        prompt: str, 
        width: int = 1024,
        height: int = 1024,
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/images/generate",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "prompt": prompt,
                    "width": width,
                    "height": height,
                    "model": "runware-xl",
                    "callback_url": callback_url if callback_url else None
                }
            )
            
            data = response.json()
            
            # Runware might return immediately with small images
            if data.get("status") == "completed":
                return {
                    "status": "completed",
                    "image_url": data["url"],
                    "image_bytes": await self._download_image(data["url"]),
                    "provider": "runware"
                }
            
            return {
                "status": "pending",
                "job_id": data["job_id"],
                "check_url": f"{self.base_url}/jobs/{data['job_id']}",
                "provider": "runware",
                "estimated_time": data.get("estimated_time", 20)
            }
    
    async def check_status(self, job_id: str) -> Dict[str, Any]:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/jobs/{job_id}",
                headers={"Authorization": f"Bearer {self.api_key}"}
            )
            
            data = response.json()
            
            if data["status"] == "completed":
                return {
                    "status": "completed",
                    "image_url": data["result"]["url"],
                    "image_bytes": await self._download_image(data["result"]["url"])
                }
            elif data["status"] == "failed":
                return {
                    "status": "failed",
                    "error": data.get("error", "Unknown error")
                }
            else:
                return {
                    "status": "processing",
                    "progress": data.get("progress", 0)
                }
    
    async def _download_image(self, url: str) -> bytes:
        async with httpx.AsyncClient() as client:
            response = await client.get(url)
            return response.content
    
    def is_async(self) -> bool:
        return True
    
    def get_cost_estimate(self, width: int, height: int) -> float:
        # Runware pricing (approximate)
        return 0.003  # Per image

# backend/api/services/generator.py

from typing import Dict, Optional, Any
import asyncio
from uuid import uuid4
from PIL import Image
import io
from ..config import supabase, config
from .providers.base import ImageProviderBase, GenerationStatus
from .providers.openai_provider import OpenAIProvider
from .providers.leonardo_provider import LeonardoProvider
from .providers.runware_provider import RunwareProvider

class ImageGenerator:
    """Main image generation service with provider abstraction."""
    
    def __init__(self, provider: Optional[str] = None):
        self.bucket_name = "images"
        
        # Initialize provider based on config or parameter
        provider_name = provider or config.IMAGE_PROVIDER or "openai"
        self.provider = self._get_provider(provider_name)
        
    def _get_provider(self, provider_name: str) -> ImageProviderBase:
        """Factory method to get appropriate provider."""
        providers = {
            "openai": lambda: OpenAIProvider(config.openai_api_key),
            "leonardo": lambda: LeonardoProvider(config.leonardo_api_key),
            "runware": lambda: RunwareProvider(config.runware_api_key),
        }
        
        if provider_name not in providers:
            raise ValueError(f"Unknown provider: {provider_name}")
        
        return providers[provider_name]()
    
    async def generate_image(
        self, 
        prompt: str, 
        style: str = "product_photography",
        callback_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """Generate image using configured provider."""
        full_prompt = self._build_prompt(prompt, style)
        
        # Start generation
        result = await self.provider.generate(
            prompt=full_prompt,
            width=2048,
            height=2048,
            callback_url=callback_url
        )
        
        if result["status"] == "completed":
            # Synchronous provider, image is ready
            return {
                "status": "completed",
                "image_bytes": result["image_bytes"],
                "provider": result.get("provider"),
                "cost": self.provider.get_cost_estimate(2048, 2048)
            }
        else:
            # Asynchronous provider, need to track job
            job_id = str(uuid4())
            
            # Store job info in database
            await self._store_generation_job(job_id, result)
            
            return {
                "status": "pending",
                "job_id": job_id,
                "provider_job_id": result["job_id"],
                "estimated_time": result.get("estimated_time", 30),
                "provider": result.get("provider")
            }
    
    async def check_generation_status(self, job_id: str) -> Dict[str, Any]:
        """Check status of async generation."""
        # Get job info from database
        job_info = await self._get_generation_job(job_id)
        
        if not job_info:
            return {"status": "not_found"}
        
        # Check with provider
        result = await self.provider.check_status(job_info["provider_job_id"])
        
        if result["status"] == "completed":
            # Update database and return image
            await self._update_job_status(job_id, "completed", result)
            return {
                "status": "completed",
                "image_bytes": result["image_bytes"],
                "cost": self.provider.get_cost_estimate(2048, 2048)
            }
        elif result["status"] == "failed":
            await self._update_job_status(job_id, "failed", result)
            return {"status": "failed", "error": result.get("error")}
        else:
            return {
                "status": "processing",
                "progress": result.get("progress", 0)
            }
    
    async def handle_webhook(self, provider: str, data: Dict[str, Any]) -> None:
        """Handle webhook callbacks from async providers."""
        # Each provider has different webhook format
        if provider == "leonardo":
            job_id = data.get("generationId")
            status = "completed" if data.get("status") == "COMPLETE" else "processing"
        elif provider == "runware":
            job_id = data.get("job_id")
            status = data.get("status")
        else:
            return
        
        # Update job status in database
        await self._update_job_from_webhook(provider, job_id, status, data)
    
    def _build_prompt(self, prompt: str, style: str) -> str:
        """Build enhanced prompt based on style."""
        style_prefixes = {
            "product_photography": "Professional product photography, clean background, studio lighting: ",
            "lifestyle": "Lifestyle photography, natural lighting, authentic setting: ",
            "artistic": "Artistic food photography, creative composition: "
        }
        return style_prefixes.get(style, "") + prompt
    
    def create_variants(self, image_bytes: bytes) -> Dict[str, bytes]:
        """Create size variants from master image."""
        variants = {}
        img = Image.open(io.BytesIO(image_bytes))
        
        sizes = {
            'thumbnail': (150, 150),
            'product_card': (400, 300),
            'full_product': (800, 600),
            'hero_image': (1920, 600),
            'full_res': (2048, 2048)
        }
        
        for name, (width, height) in sizes.items():
            variant = self._resize_and_crop(img, width, height)
            buffer = io.BytesIO()
            variant.save(buffer, format='JPEG', quality=90)
            variants[name] = buffer.getvalue()
            
        return variants
    
    async def upload_to_supabase(
        self, 
        image_bytes: bytes, 
        image_id: str,
        size_preset: str
    ) -> Dict[str, str]:
        """Upload image to Supabase Storage and return URLs."""
        file_path = f"{image_id}/{size_preset}.jpg"
        
        # Upload to Supabase Storage
        response = supabase.storage.from_(self.bucket_name).upload(
            path=file_path,
            file=image_bytes,
            file_options={"content-type": "image/jpeg"}
        )
        
        # Get public URL
        public_url = supabase.storage.from_(self.bucket_name).get_public_url(file_path)
        
        return {
            "storage_path": file_path,
            "public_url": public_url
        }
    
    def extract_colors(self, image_bytes: bytes) -> List[Dict]:
        """Extract dominant colors from image."""
        from colorthief import ColorThief
        
        color_thief = ColorThief(io.BytesIO(image_bytes))
        palette = color_thief.get_palette(color_count=5, quality=1)
        
        colors = []
        for i, rgb in enumerate(palette):
            hex_color = '#{:02x}{:02x}{:02x}'.format(*rgb)
            colors.append({
                "color_hex": hex_color,
                "percentage": (5-i) * 20,  # Simple percentage distribution
                "is_dominant": i == 0
            })
        
        return colors
```

### Auto-Tagging Service

```python
# backend/api/services/tagger.py

import json
from typing import List, Dict, Optional
import openai
import base64
from ..config import config

class AutoTagger:
    def __init__(self):
        openai.api_key = config.openai_api_key
        self.openai_client = openai.AsyncClient()
    
    async def analyze_and_tag(
        self,
        image_bytes: bytes,
        original_prompt: str,
        colors: List[str]
    ) -> Dict:
        """
        Use GPT-4 Vision to analyze image and generate tags.
        """
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode()
        
        # Vision analysis
        vision_response = await self.openai_client.chat.completions.create(
            model="gpt-4-vision-preview",
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this cottage food product image and provide:
                        1. Main food item(s)
                        2. Presentation style
                        3. Props/surfaces
                        4. Visual style/mood
                        5. Color characteristics
                        Return as JSON."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }],
            max_tokens=500
        )
        
        vision_analysis = json.loads(vision_response.choices[0].message.content)
        
        # Generate tags based on vision + context
        tags_response = await self.openai_client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{
                "role": "system",
                "content": "You are an expert at generating search tags for cottage food product images."
            }, {
                "role": "user",
                "content": f"""
                Original prompt: {original_prompt}
                Vision analysis: {json.dumps(vision_analysis)}
                
                Generate 8-12 specific search tags that cottage food businesses would use.
                Include: food type, category, visual descriptors, presentation style.
                Return as JSON: {{"tags": [...], "category": "...", "description": "..."}}
                """
            }],
            response_format={"type": "json_object"}
        )
        
        tags_data = json.loads(tags_response.choices[0].message.content)
        
        return {
            "tags": tags_data["tags"],
            "category": tags_data["category"],
            "description": tags_data["description"],
            "vision_analysis": vision_analysis,
            "confidence": 0.9  # Calculate based on vision confidence
        }
```

### Database Service with Supabase

```python
# backend/api/services/database.py

from typing import List, Dict, Optional
from uuid import UUID
from ..config import supabase
import json

class DatabaseService:
    
    async def create_image(self, data: Dict) -> Dict:
        """Create new image record."""
        response = supabase.table('images').insert(data).execute()
        return response.data[0]
    
    async def update_image(self, image_id: str, data: Dict) -> Dict:
        """Update image record."""
        response = supabase.table('images').update(data).eq('id', image_id).execute()
        return response.data[0]
    
    async def create_variants(self, variants_data: List[Dict]) -> List[Dict]:
        """Bulk create image variants."""
        response = supabase.table('image_variants').insert(variants_data).execute()
        return response.data
    
    async def create_tags(self, tags_data: List[Dict]) -> List[Dict]:
        """Bulk create image tags."""
        response = supabase.table('image_tags').insert(tags_data).execute()
        return response.data
    
    async def create_embedding(self, embedding_data: Dict) -> Dict:
        """Store embedding vector."""
        # Convert list to proper vector format for Supabase
        embedding_data['embedding'] = json.dumps(embedding_data['embedding'])
        response = supabase.table('image_embeddings').insert(embedding_data).execute()
        return response.data[0]
    
    async def vector_search(
        self, 
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
        size_preset: str = "product_card"
    ) -> List[Dict]:
        """Search for similar images using pgvector via Supabase RPC."""
        response = supabase.rpc(
            'search_similar_images',
            {
                'query_embedding': query_embedding,
                'match_threshold': threshold,
                'match_count': limit,
                'size_preset': size_preset
            }
        ).execute()
        
        return response.data
    
    async def get_review_queue(self, limit: int = 20) -> List[Dict]:
        """Get images pending review."""
        response = supabase.table('images')\
            .select('*, image_tags(*), image_descriptions(*)')\
            .eq('status', 'ready')\
            .order('created_at', desc=True)\
            .limit(limit)\
            .execute()
        
        return response.data
    
    async def approve_image(self, image_id: str, user_id: str) -> Dict:
        """Approve image for search."""
        response = supabase.table('images')\
            .update({
                'status': 'approved',
                'approved_at': 'now()',
                'approved_by': user_id
            })\
            .eq('id', image_id)\
            .execute()
        
        return response.data[0]
```

### Embedding Service

```python
# backend/api/services/embeddings.py

import openai
import numpy as np
from typing import List, Optional
from ..config import config

class EmbeddingService:
    def __init__(self):
        openai.api_key = config.openai_api_key
        self.openai_client = openai.AsyncClient()
        
    async def create_embedding(self, text: str) -> List[float]:
        """Generate embedding for search text."""
        response = await self.openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    
    async def create_image_embedding(
        self,
        prompt: str,
        tags: List[str],
        description: str,
        category: str
    ) -> List[float]:
        """Create rich embedding for image searchability."""
        # Combine all text elements
        combined_text = " ".join([
            prompt,
            description,
            category,
            " ".join(tags)
        ])
        
        return await self.create_embedding(combined_text)
```

### Authentication Service

```python
# backend/api/services/auth.py

from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from ..config import supabase
from typing import Optional, Dict

security = HTTPBearer()

async def verify_token(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict:
    """Verify Supabase auth token."""
    token = credentials.credentials
    
    try:
        # Verify with Supabase
        user = supabase.auth.get_user(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token"
            )
        return user.user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials"
        )

async def verify_api_key(api_key: str) -> bool:
    """Verify API key for search endpoint."""
    import hashlib
    
    # Hash the API key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Check in database
    response = supabase.table('api_keys')\
        .select('*')\
        .eq('key_hash', key_hash)\
        .eq('is_active', True)\
        .execute()
    
    if not response.data:
        return False
    
    # Update last used timestamp
    supabase.table('api_keys')\
        .update({'last_used_at': 'now()'})\
        .eq('id', response.data[0]['id'])\
        .execute()
    
    return True
```

## 7. Frontend Components

### Supabase Setup

```tsx
// frontend/src/lib/supabase.ts
import { createClient } from '@supabase/supabase-js'

const supabaseUrl = process.env.REACT_APP_SUPABASE_URL!
const supabaseAnonKey = process.env.REACT_APP_SUPABASE_ANON_KEY!

export const supabase = createClient(supabaseUrl, supabaseAnonKey)

// Type definitions for database
export type Database = {
  public: {
    Tables: {
      images: {
        Row: {
          id: string
          prompt: string
          status: string
          created_at: string
          // ... other fields
        }
      }
    }
  }
}
```

### Main App Structure

```tsx
// frontend/src/App.tsx
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Toaster } from 'sonner';
import { useEffect, useState } from 'react';
import { Session } from '@supabase/supabase-js';
import { supabase } from './lib/supabase';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Generate from './pages/Generate';
import Review from './pages/Review';
import Library from './pages/Library';

const queryClient = new QueryClient();

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session } }) => {
      setSession(session);
      setLoading(false);
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      setSession(session);
    });

    return () => subscription.unsubscribe();
  }, []);

  if (loading) {
    return <div>Loading...</div>;
  }

  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="min-h-screen bg-gray-50">
          {session ? (
            <>
              <Navigation session={session} />
              <Routes>
                <Route path="/" element={<Dashboard />} />
                <Route path="/generate" element={<Generate />} />
                <Route path="/review" element={<Review />} />
                <Route path="/library" element={<Library />} />
              </Routes>
            </>
          ) : (
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route path="*" element={<Navigate to="/login" />} />
            </Routes>
          )}
          <Toaster />
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

### Login Page

```tsx
// frontend/src/pages/Login.tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { supabase } from '../lib/supabase';
import { toast } from 'sonner';

export default function Login() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);

    const { error } = await supabase.auth.signInWithPassword({
      email,
      password,
    });

    if (error) {
      toast.error(error.message);
    } else {
      navigate('/');
    }
    setLoading(false);
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <form onSubmit={handleLogin} className="w-full max-w-md space-y-4">
        <h1 className="text-2xl font-bold">Admin Login</h1>
        <input
          type="email"
          placeholder="Email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full px-3 py-2 border rounded"
          required
        />
        <input
          type="password"
          placeholder="Password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full px-3 py-2 border rounded"
          required
        />
        <button
          type="submit"
          disabled={loading}
          className="w-full bg-blue-500 text-white py-2 rounded"
        >
          {loading ? 'Loading...' : 'Login'}
        </button>
      </form>
    </div>
  );
}
```

### Generate Page

```tsx
// frontend/src/pages/Generate.tsx
import { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { ChromePicker } from 'react-color';
import { toast } from 'sonner';
import { supabase } from '../lib/supabase';

const COTTAGE_FOOD_TEMPLATES = {
  cookies: {
    prompts: [
      "chocolate chip cookies on {surface}",
      "sugar cookies with frosting on {surface}",
    ],
    surfaces: ["white plate", "wooden board"],
  },
  // ... other templates
};

interface Provider {
  id: string;
  name: string;
  is_async: boolean;
  cost_per_image: number;
  available: boolean;
  features: string[];
}

export default function Generate() {
  const [colors, setColors] = useState(['#E8F4F8', '#FFF5E6']);
  const [generating, setGenerating] = useState(false);
  const [providers, setProviders] = useState<Provider[]>([]);
  const [selectedProvider, setSelectedProvider] = useState('openai');
  const [asyncJobId, setAsyncJobId] = useState<string | null>(null);
  const { register, handleSubmit } = useForm();

  useEffect(() => {
    loadProviders();
  }, []);

  useEffect(() => {
    // Poll for async job status
    if (asyncJobId) {
      const interval = setInterval(async () => {
        const status = await checkJobStatus(asyncJobId);
        if (status.status === 'completed' || status.status === 'failed') {
          setAsyncJobId(null);
          if (status.status === 'completed') {
            toast.success('Images generated successfully!');
          } else {
            toast.error('Generation failed');
          }
        } else {
          toast.info(`Progress: ${status.progress}%`);
        }
      }, 2000);
      
      return () => clearInterval(interval);
    }
  }, [asyncJobId]);

  const loadProviders = async () => {
    const token = (await supabase.auth.getSession()).data.session?.access_token;
    
    const response = await fetch('/api/admin/providers', {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    if (response.ok) {
      const data = await response.json();
      setProviders(Object.entries(data).map(([id, info]: any) => ({
        id,
        ...info
      })));
    }
  };

  const checkJobStatus = async (jobId: string) => {
    const token = (await supabase.auth.getSession()).data.session?.access_token;
    
    const response = await fetch(`/api/admin/generate/status/${jobId}`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });
    
    return response.json();
  };

  const onSubmit = async (data: any) => {
    setGenerating(true);
    try {
      const token = (await supabase.auth.getSession()).data.session?.access_token;
      
      const response = await fetch('/api/admin/generate/batch', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`,
        },
        body: JSON.stringify({
          prompts: data.prompts,
          colors: colors,
          style: data.style,
          count_per_prompt: data.count,
          provider: selectedProvider,
        }),
      });

      if (!response.ok) throw new Error('Generation failed');
      
      const result = await response.json();
      
      if (result.is_async) {
        // Async provider - start polling
        setAsyncJobId(result.job_id);
        toast.info(`Generation started with ${selectedProvider}. This may take ${result.estimated_time || 30} seconds...`);
        
        // Subscribe to realtime updates if available
        const channel = supabase
          .channel(`job-${result.job_id}`)
          .on('broadcast', { event: 'generation_update' }, (payload) => {
            toast.info(`${payload.status}: ${payload.message}`);
          })
          .subscribe();
      } else {
        // Sync provider - immediate result
        toast.success('Images generated successfully!');
      }
      
    } catch (error) {
      toast.error('Failed to start generation');
    } finally {
      setGenerating(false);
    }
  };

  const selectedProviderInfo = providers.find(p => p.id === selectedProvider);

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Generate Images</h1>
      
      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Provider Selection */}
        <div className="bg-blue-50 p-4 rounded">
          <label className="block text-sm font-medium mb-2">Image Provider</label>
          <select 
            value={selectedProvider}
            onChange={(e) => setSelectedProvider(e.target.value)}
            className="w-full p-2 border rounded mb-2"
          >
            {providers.filter(p => p.available).map(provider => (
              <option key={provider.id} value={provider.id}>
                {provider.name} - ${provider.cost_per_image}/image
                {provider.is_async ? ' (async)' : ' (instant)'}
              </option>
            ))}
          </select>
          
          {selectedProviderInfo && (
            <div className="text-sm text-gray-600">
              <p>Cost: ${selectedProviderInfo.cost_per_image} per image</p>
              <p>Type: {selectedProviderInfo.is_async ? 'Asynchronous (webhook/polling)' : 'Synchronous (instant)'}</p>
              <p>Features: {selectedProviderInfo.features.join(', ')}</p>
            </div>
          )}
        </div>

        {/* Template selector */}
        <div>
          <label className="block text-sm font-medium mb-2">Templates</label>
          <select {...register('template')} className="w-full p-2 border rounded">
            {Object.keys(COTTAGE_FOOD_TEMPLATES).map(key => (
              <option key={key} value={key}>{key}</option>
            ))}
          </select>
        </div>

        {/* Color palette */}
        <div>
          <label className="block text-sm font-medium mb-2">Colors</label>
          <div className="flex gap-2">
            {colors.map((color, idx) => (
              <div
                key={idx}
                className="w-12 h-12 rounded cursor-pointer border-2 border-gray-300"
                style={{ backgroundColor: color }}
                onClick={() => {/* Open color picker */}}
              />
            ))}
            <button
              type="button"
              className="w-12 h-12 rounded border-2 border-dashed border-gray-400 flex items-center justify-center"
              onClick={() => setColors([...colors, '#FFFFFF'])}
            >
              +
            </button>
          </div>
        </div>

        {/* Progress indicator for async jobs */}
        {asyncJobId && (
          <div className="bg-yellow-50 p-4 rounded">
            <p className="text-sm font-medium">Generation in progress...</p>
            <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
              <div className="bg-blue-600 h-2 rounded-full" style={{ width: '45%' }}></div>
            </div>
          </div>
        )}

        {/* Submit */}
        <button
          type="submit"
          disabled={generating || !!asyncJobId}
          className="bg-blue-500 text-white px-4 py-2 rounded disabled:opacity-50"
        >
          {generating ? 'Starting...' : asyncJobId ? 'Processing...' : 'Generate Batch'}
        </button>
      </form>
    </div>
  );
}
```

### Review Page with Supabase Realtime

```tsx
// frontend/src/pages/Review.tsx
import { useEffect, useState } from 'react';
import { supabase } from '../lib/supabase';
import { toast } from 'sonner';

export default function Review() {
  const [images, setImages] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadReviewQueue();
    
    // Subscribe to changes
    const subscription = supabase
      .channel('images-changes')
      .on(
        'postgres_changes',
        {
          event: '*',
          schema: 'public',
          table: 'images',
          filter: 'status=eq.ready',
        },
        (payload) => {
          if (payload.eventType === 'INSERT') {
            setImages(prev => [payload.new, ...prev]);
          }
        }
      )
      .subscribe();

    return () => {
      subscription.unsubscribe();
    };
  }, []);

  const loadReviewQueue = async () => {
    const { data, error } = await supabase
      .from('images')
      .select(`
        *,
        image_tags(*),
        image_descriptions(*),
        image_variants(*)
      `)
      .eq('status', 'ready')
      .order('created_at', { ascending: false })
      .limit(20);

    if (error) {
      toast.error('Failed to load review queue');
    } else {
      setImages(data || []);
    }
    setLoading(false);
  };

  const approveImage = async (imageId: string) => {
    const { error } = await supabase
      .from('images')
      .update({ 
        status: 'approved',
        approved_at: new Date().toISOString(),
        approved_by: (await supabase.auth.getUser()).data.user?.id
      })
      .eq('id', imageId);

    if (error) {
      toast.error('Failed to approve image');
    } else {
      toast.success('Image approved');
      setImages(prev => prev.filter(img => img.id !== imageId));
    }
  };

  if (loading) return <div>Loading...</div>;

  return (
    <div className="max-w-6xl mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Review Queue</h1>
      
      <div className="grid grid-cols-2 gap-6">
        {images.map(image => (
          <div key={image.id} className="border rounded p-4">
            <img
              src={image.image_variants[0]?.public_url}
              alt={image.prompt}
              className="w-full h-48 object-cover mb-4"
            />
            <p className="text-sm mb-2">{image.prompt}</p>
            <div className="flex flex-wrap gap-1 mb-4">
              {image.image_tags?.map((tag: any) => (
                <span
                  key={tag.tag}
                  className="px-2 py-1 bg-gray-100 text-xs rounded"
                >
                  {tag.tag}
                </span>
              ))}
            </div>
            <div className="flex gap-2">
              <button
                onClick={() => approveImage(image.id)}
                className="bg-green-500 text-white px-3 py-1 rounded"
              >
                Approve
              </button>
              <button className="bg-red-500 text-white px-3 py-1 rounded">
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

## 8. Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Supabase Local Development Stack
  supabase-db:
    image: supabase/postgres:15.1.0.117
    command:
      - postgres
      - -c
      - config_file=/etc/postgresql/postgresql.conf
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./scripts/init.sql:/docker-entrypoint-initdb.d/init.sql

  supabase-studio:
    image: supabase/studio:latest
    ports:
      - "3001:3000"
    environment:
      STUDIO_PG_META_URL: http://supabase-db:5432
      POSTGRES_PASSWORD: postgres
      DEFAULT_ORGANIZATION: Default
      DEFAULT_PROJECT: AIWebImageService
    depends_on:
      - supabase-db

  supabase-storage:
    image: supabase/storage-api:v0.40.4
    ports:
      - "5001:5000"
    environment:
      ANON_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      SERVICE_KEY: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
      DATABASE_URL: postgresql://postgres:postgres@supabase-db:5432/postgres
      PGRST_JWT_SECRET: super-secret-jwt-token-with-at-least-32-characters-long
      FILE_SIZE_LIMIT: 52428800
      STORAGE_BACKEND: file
      FILE_STORAGE_BACKEND_PATH: /var/lib/storage
    volumes:
      - storage_data:/var/lib/storage
    depends_on:
      - supabase-db

  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    ports:
      - "8000:8000"
    environment:
      SUPABASE_URL: http://localhost:8000
      SUPABASE_SERVICE_KEY: ${SUPABASE_SERVICE_KEY}
      DATABASE_URL: postgresql://postgres:postgres@supabase-db:5432/postgres
      OPENAI_API_KEY: ${OPENAI_API_KEY}
      GCP_PROJECT_ID: ${GCP_PROJECT_ID}
      ENV: development
    depends_on:
      - supabase-db
      - supabase-storage
    volumes:
      - ./backend:/app
    command: uvicorn api.main:app --reload --host 0.0.0.0

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    ports:
      - "3000:3000"
    environment:
      REACT_APP_SUPABASE_URL: http://localhost:8000
      REACT_APP_SUPABASE_ANON_KEY: ${SUPABASE_ANON_KEY}
      REACT_APP_API_URL: http://localhost:8000
    volumes:
      - ./frontend:/app
      - /app/node_modules
    command: npm start

volumes:
  postgres_data:
  storage_data:
```

### Production Dockerfile for Cloud Run

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Cloud Run expects port 8080
ENV PORT 8080
EXPOSE 8080

# Run with uvicorn
CMD exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT}
```

```dockerfile
# frontend/Dockerfile
FROM node:18-alpine as builder

WORKDIR /app

# Copy package files
COPY package*.json ./
RUN npm ci

# Copy source and build
COPY . .
RUN npm run build

# Production stage
FROM nginx:alpine
COPY --from=builder /app/build /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

## 9. Environment Variables

```bash
# backend/.env.example

# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Service role key for backend
SUPABASE_ANON_KEY=eyJ...     # Anon key for frontend

# Google Cloud Platform
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=/path/to/service-account.json  # For local dev

# Image Generation Providers (configure at least one)
IMAGE_PROVIDER=openai  # Default provider: openai, leonardo, runware

## OpenAI (DALL-E 3)
OPENAI_API_KEY=sk-...
OPENAI_ORG_ID=org-...  # Optional

## Leonardo.ai
LEONARDO_API_KEY=...  # Get from leonardo.ai dashboard

## Runware
RUNWARE_API_KEY=...  # Get from runware.ai

# AI Model Settings (for tagging/embeddings)
VISION_MODEL=gpt-4-vision-preview
EMBEDDING_MODEL=text-embedding-ada-002
LLM_MODEL=gpt-4-turbo-preview

# Application Settings
ENV=development  # or production
API_V1_PREFIX=/api/v1
CORS_ORIGINS=["http://localhost:3000"]

# Webhook Configuration (for async providers)
WEBHOOK_BASE_URL=https://your-api.run.app  # Your deployed API URL
WEBHOOK_SECRET=your-webhook-secret  # For validating webhooks

# Feature Flags
AUTO_TAG_ENABLED=true
MIN_TAG_CONFIDENCE=0.7
MAX_TAGS_PER_IMAGE=12
ENABLE_ASYNC_PROVIDERS=true

# Rate Limiting
DEFAULT_RATE_LIMIT=100
```

```bash
# frontend/.env.example

# Supabase
REACT_APP_SUPABASE_URL=https://your-project.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJ...

# API Backend (Cloud Run URL in production)
REACT_APP_API_URL=http://localhost:8000  # or https://your-service-xxxxx-uc.a.run.app

# Environment
REACT_APP_ENV=development

# Feature Flags
REACT_APP_ENABLE_PROVIDER_SELECTION=true  # Show provider dropdown in UI
```

## 10. Testing Strategy

```python
# scripts/test_search.py

import asyncio
import httpx
import time

async def test_search_api():
    """Test search API performance and accuracy."""
    
    test_queries = [
        "chocolate chip cookies on white plate",
        "rustic sourdough bread",
        "decorated birthday cake",
        "jar of strawberry jam"
    ]
    
    async with httpx.AsyncClient() as client:
        for query in test_queries:
            start = time.time()
            
            response = await client.post(
                "http://localhost:8000/api/v1/search",
                json={"query": query, "limit": 5},
                headers={"X-API-Key": "test-key"}
            )
            
            elapsed = (time.time() - start) * 1000
            results = response.json()
            
            print(f"Query: '{query}'")
            print(f"Time: {elapsed:.2f}ms")
            print(f"Results: {len(results['results'])}")
            print(f"Top match score: {results['results'][0]['score']:.3f}")
            print("---")

if __name__ == "__main__":
    asyncio.run(test_search_api())
```

## 11. Deployment Instructions

### Prerequisites

1. **Supabase Project Setup**
   ```bash
   # Create a new project at https://supabase.com
   # Note your project URL and keys
   ```

2. **GCP Project Setup**
   ```bash
   # Install gcloud CLI
   gcloud auth login
   gcloud config set project YOUR_PROJECT_ID
   
   # Enable required APIs
   gcloud services enable run.googleapis.com
   gcloud services enable secretmanager.googleapis.com
   gcloud services enable cloudbuild.googleapis.com
   ```

### Step 1: Configure Supabase

```sql
-- Run in Supabase SQL Editor
-- 1. Create storage bucket
INSERT INTO storage.buckets (id, name, public) 
VALUES ('images', 'images', true);

-- 2. Run schema from section 4
-- (Copy and paste the entire schema)

-- 3. Create admin user
INSERT INTO auth.users (email, encrypted_password, email_confirmed_at, role)
VALUES ('admin@example.com', crypt('your-password', gen_salt('bf')), now(), 'authenticated');
```

### Step 2: Store Secrets in GCP

```bash
# Create secrets in Secret Manager
echo -n "your-supabase-service-key" | gcloud secrets create supabase-service-key --data-file=-
echo -n "your-openai-api-key" | gcloud secrets create openai-api-key --data-file=-

# Grant Cloud Run access to secrets
gcloud secrets add-iam-policy-binding supabase-service-key \
  --member="serviceAccount:YOUR_PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

### Step 3: Deploy Backend to Cloud Run

```bash
# Build and deploy
cd backend

# Build container
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/aiwebimage-api

# Deploy to Cloud Run
gcloud run deploy aiwebimage-api \
  --image gcr.io/YOUR_PROJECT_ID/aiwebimage-api \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="SUPABASE_URL=https://your-project.supabase.co,GCP_PROJECT_ID=YOUR_PROJECT_ID" \
  --set-secrets="SUPABASE_SERVICE_KEY=supabase-service-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
  --min-instances=0 \
  --max-instances=10 \
  --memory=1Gi

# Note the service URL
export API_URL=https://aiwebimage-api-xxxxx-uc.a.run.app
```

### Step 4: Deploy Frontend

```bash
cd frontend

# Update .env with production URLs
echo "REACT_APP_SUPABASE_URL=https://your-project.supabase.co" > .env
echo "REACT_APP_SUPABASE_ANON_KEY=your-anon-key" >> .env
echo "REACT_APP_API_URL=$API_URL" >> .env

# Build
npm run build

# Option 1: Deploy to Cloud Run
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/aiwebimage-frontend
gcloud run deploy aiwebimage-frontend \
  --image gcr.io/YOUR_PROJECT_ID/aiwebimage-frontend \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --port 80

# Option 2: Deploy to Firebase Hosting
npm install -g firebase-tools
firebase init hosting
firebase deploy
```

### Step 5: Configure Cloud CDN (Optional)

```bash
# Create backend bucket for Cloud CDN
gsutil mb gs://YOUR_PROJECT_ID-cdn

# Configure load balancer with Cloud CDN
gcloud compute backend-buckets create aiwebimage-cdn \
  --gcs-bucket-name=YOUR_PROJECT_ID-cdn

gcloud compute backend-buckets update aiwebimage-cdn \
  --enable-cdn \
  --cache-mode=CACHE_ALL_STATIC
```

### Step 6: Initialize Data

```bash
# Run initialization script
cd scripts
python init_data.py

# Or use the CLI
python cli.py generate "chocolate chip cookies" --count 5
python cli.py generate "sourdough bread" --count 5
```

### Monitoring Setup

```bash
# Set up Cloud Monitoring dashboard
gcloud monitoring dashboards create --config-from-file=monitoring/dashboard.json

# Set up alerts
gcloud alpha monitoring policies create --config-from-file=monitoring/alerts.yaml
```

### Production Checklist

- [ ] Supabase project created and configured
- [ ] Database schema applied
- [ ] Storage bucket created
- [ ] Secrets stored in GCP Secret Manager
- [ ] Backend deployed to Cloud Run
- [ ] Frontend deployed
- [ ] DNS configured (if using custom domain)
- [ ] SSL certificates active
- [ ] Monitoring dashboards created
- [ ] Initial images generated and approved
- [ ] API keys created for search endpoint
- [ ] Rate limiting configured
- [ ] Backup strategy in place

## 12. CLI Commands for Development

```bash
# backend/scripts/cli.py

import typer
from typing import List
import asyncio

app = typer.Typer()

@app.command()
def generate(
    prompt: str,
    colors: List[str] = typer.Option(["#FFFFFF"]),
    count: int = 1
):
    """Generate images from command line."""
    asyncio.run(_generate(prompt, colors, count))

@app.command()
def search(query: str, limit: int = 5):
    """Test search functionality."""
    asyncio.run(_search(query, limit))

@app.command()
def approve(image_id: str):
    """Approve an image."""
    asyncio.run(_approve(image_id))

@app.command()
def stats():
    """Show system statistics."""
    asyncio.run(_show_stats())

if __name__ == "__main__":
    app()
```

## 13. Error Handling

```python
# backend/api/middleware/error_handler.py

from fastapi import Request, status
from fastapi.responses import JSONResponse
import logging

logger = logging.getLogger(__name__)

async def error_handler(request: Request, exc: Exception):
    """Global error handler for API."""
    
    if isinstance(exc, ValueError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)}
        )
    
    if isinstance(exc, PermissionError):
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Permission denied"}
        )
    
    # Log unexpected errors
    logger.error(f"Unhandled error: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )
```

## 14. Performance Optimizations

```python
# backend/api/services/cache.py

from typing import Optional, Dict, Any
import hashlib
import json
from datetime import datetime, timedelta
from ..config import supabase

class CacheService:
    """Use Supabase for caching instead of Redis."""
    
    def __init__(self):
        # Create cache table if not exists
        self.cache_table = 'search_cache'
    
    async def get_search_cache(self, query: str, size: str) -> Optional[dict]:
        """Get cached search results from Supabase."""
        cache_key = self._generate_cache_key(query, size)
        
        response = supabase.table(self.cache_table)\
            .select('*')\
            .eq('cache_key', cache_key)\
            .gt('expires_at', datetime.now().isoformat())\
            .execute()
        
        if response.data:
            return json.loads(response.data[0]['results'])
        return None
    
    async def set_search_cache(
        self, 
        query: str,
        size: str,
        results: dict, 
        ttl_minutes: int = 60
    ):
        """Cache search results in Supabase."""
        cache_key = self._generate_cache_key(query, size)
        expires_at = datetime.now() + timedelta(minutes=ttl_minutes)
        
        # Upsert cache entry
        supabase.table(self.cache_table).upsert({
            'cache_key': cache_key,
            'query': query,
            'size': size,
            'results': json.dumps(results),
            'expires_at': expires_at.isoformat(),
            'created_at': datetime.now().isoformat()
        }).execute()
    
    def _generate_cache_key(self, query: str, size: str) -> str:
        """Generate deterministic cache key."""
        combined = f"{query.lower().strip()}:{size}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    async def cleanup_expired(self):
        """Remove expired cache entries."""
        supabase.table(self.cache_table)\
            .delete()\
            .lt('expires_at', datetime.now().isoformat())\
            .execute()

# SQL for cache table
"""
CREATE TABLE IF NOT EXISTS search_cache (
    cache_key VARCHAR(32) PRIMARY KEY,
    query TEXT NOT NULL,
    size VARCHAR(20),
    results JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cache_expires ON search_cache(expires_at);
"""

# Using Supabase Edge Functions for performance
"""
// supabase/functions/search-images/index.ts
import { serve } from 'https://deno.land/std@0.168.0/http/server.ts'
import { createClient } from 'https://esm.sh/@supabase/supabase-js@2'

serve(async (req) => {
  const { query, size = 'product_card' } = await req.json()
  
  const supabase = createClient(
    Deno.env.get('SUPABASE_URL'),
    Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')
  )
  
  // Check cache first
  const cacheKey = crypto.subtle.digest('MD5', new TextEncoder().encode(`${query}:${size}`))
  
  // Call RPC function for vector search
  const { data, error } = await supabase.rpc('search_similar_images', {
    query_embedding: await generateEmbedding(query),
    match_threshold: 0.7,
    match_count: 10,
    size_preset: size
  })
  
  return new Response(JSON.stringify({ results: data }), {
    headers: { 'Content-Type': 'application/json' },
  })
})
"""
```

## 15. Monitoring Setup

```python
# backend/api/monitoring.py

from prometheus_client import Counter, Histogram, Gauge
import time

# Metrics
search_requests = Counter('search_requests_total', 'Total search requests')
search_latency = Histogram('search_latency_seconds', 'Search request latency')
active_generations = Gauge('active_generations', 'Currently processing generations')
approved_images = Counter('approved_images_total', 'Total approved images')

def track_search(func):
    """Decorator to track search metrics."""
    async def wrapper(*args, **kwargs):
        search_requests.inc()
        start = time.time()
        try:
            result = await func(*args, **kwargs)
            return result
        finally:
            search_latency.observe(time.time() - start)
    return wrapper
```

## Summary

This architecture document is optimized for Claude Code implementation using only **Supabase** and **Google Cloud Platform**, providing:

### Key Advantages of This Stack:

1. **Simplified Infrastructure** - Only 2 services to manage (Supabase + GCP)
2. **Built-in Features** - pgvector, auth, storage, and realtime all included in Supabase
3. **Cost Efficient** - Both services have generous free tiers, scales to zero with Cloud Run
4. **Developer Experience** - Supabase Studio for database management, excellent documentation

### What Supabase Provides:
- PostgreSQL with **pgvector pre-enabled** (no setup required!)
- Authentication system (no custom auth needed)
- Object storage with CDN URLs
- Realtime subscriptions for live updates
- Row-level security for API management
- SQL editor and dashboard

### What GCP Provides:
- Cloud Run for serverless backend (scales to zero)
- Secret Manager for API keys
- Cloud CDN for global distribution
- Cloud Monitoring for observability
- Cloud Build for CI/CD

### Implementation Ready:
- **Complete project structure** with file organization
- **Full database schema** with Supabase-specific features
- **Service implementations** using Supabase client
- **Frontend components** with Supabase auth integration
- **Docker setup** for local development
- **Deployment instructions** for Cloud Run
- **Cost optimization** through serverless architecture

Claude Code can use this document to build the entire application systematically, with all technical decisions made for the Supabase + GCP stack. The architecture eliminates complexity while maintaining all required functionality for the cottage food image service.