# AIWebImageService - GCP + Supabase Deployment Architecture

## Overview
This document shows how to deploy the entire AIWebImageService using only Google Cloud Platform (GCP) and Supabase, eliminating the need for multiple service subscriptions.

## Service Mapping

### What Supabase Provides
- **PostgreSQL Database** with pgvector extension (built-in!)
- **Authentication** (replaces custom auth)
- **Row Level Security** (RLS) for API keys
- **Realtime subscriptions** (for job status)
- **Storage** (replaces S3/MinIO)
- **Edge Functions** (optional - for lightweight operations)

### What GCP Provides
- **Cloud Run** - Host the FastAPI backend
- **Cloud Run** - Host the React frontend (or Firebase Hosting)
- **Cloud CDN** - Global image delivery
- **Cloud Storage** - Backup/archive (optional, Supabase Storage is primary)
- **Cloud Scheduler** - Batch jobs
- **Secret Manager** - API keys management

## Revised Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Supabase                              │
├─────────────────────────────────────────────────────────┤
│  • PostgreSQL with pgvector (built-in!)                  │
│  • Auth (admin users)                                    │
│  • Storage (images)                                      │
│  • Realtime (job updates)                                │
└─────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────┐
│                  Google Cloud Run                        │
├─────────────────────────────────────────────────────────┤
│  • FastAPI Backend (containerized)                       │
│  • Image Generation Service                              │
│  • Auto-tagging Service                                  │
│  • Search API                                            │
└─────────────────────────────────────────────────────────┘
                            ↕
┌─────────────────────────────────────────────────────────┐
│              Google Cloud CDN + Storage                  │
├─────────────────────────────────────────────────────────┤
│  • CDN for Supabase Storage URLs                         │
│  • Optional: Direct GCS for heavy traffic                │
└─────────────────────────────────────────────────────────┘

```

## Implementation Changes

### 1. Database Setup (Supabase)

```sql
-- Supabase already has pgvector enabled!
-- Just create your tables:

CREATE TABLE images (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    prompt TEXT NOT NULL,
    style VARCHAR(50) DEFAULT 'product_photography',
    status VARCHAR(20) DEFAULT 'pending',
    -- ... rest of schema from ARCHITECTURE.md
);

-- Enable RLS for API access
ALTER TABLE images ENABLE ROW LEVEL SECURITY;

-- Create storage bucket for images
INSERT INTO storage.buckets (id, name, public) 
VALUES ('images', 'images', true);
```

### 2. Backend Changes for Supabase

```python
# backend/api/config.py
from supabase import create_client, Client
import os

# Initialize Supabase client
supabase: Client = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")  # Use service key for backend
)

# backend/api/services/storage.py
class StorageService:
    def __init__(self):
        self.bucket = "images"
    
    async def upload_image(self, file_bytes: bytes, path: str) -> str:
        """Upload to Supabase Storage instead of S3."""
        response = supabase.storage.from_(self.bucket).upload(
            path=path,
            file=file_bytes,
            file_options={"content-type": "image/jpeg"}
        )
        
        # Get public URL
        url = supabase.storage.from_(self.bucket).get_public_url(path)
        return url

# backend/api/services/database.py
class DatabaseService:
    async def vector_search(self, embedding: list, limit: int = 10):
        """Use Supabase's pgvector through PostgREST."""
        response = supabase.rpc(
            'search_similar_images',
            {
                'query_embedding': embedding,
                'match_threshold': 0.7,
                'match_count': limit
            }
        ).execute()
        
        return response.data
```

### 3. Authentication with Supabase Auth

```python
# backend/api/auth.py
from fastapi import HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Verify Supabase auth token."""
    token = credentials.credentials
    
    try:
        user = supabase.auth.get_user(token)
        return user
    except Exception as e:
        raise HTTPException(status_code=401, detail="Invalid token")

# Use in routes:
@router.post("/admin/generate")
async def generate_images(
    request: GenerateRequest,
    user = Depends(verify_token)
):
    # Only authenticated users can generate
    pass
```

### 4. Frontend Changes

```typescript
// frontend/src/services/supabase.ts
import { createClient } from '@supabase/supabase-js'

export const supabase = createClient(
  process.env.REACT_APP_SUPABASE_URL!,
  process.env.REACT_APP_SUPABASE_ANON_KEY!
)

// frontend/src/services/auth.ts
export const signIn = async (email: string, password: string) => {
  const { data, error } = await supabase.auth.signInWithPassword({
    email,
    password,
  })
  return { data, error }
}

// frontend/src/services/storage.ts
export const getImageUrl = (path: string) => {
  return supabase.storage.from('images').getPublicUrl(path).data.publicUrl
}
```

### 5. Cloud Run Deployment

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

```yaml
# backend/cloudbuild.yaml
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/aiwebimage-api', '.']
  
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/aiwebimage-api']
  
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'aiwebimage-api'
      - '--image=gcr.io/$PROJECT_ID/aiwebimage-api'
      - '--region=us-central1'
      - '--platform=managed'
      - '--allow-unauthenticated'
      - '--set-env-vars=SUPABASE_URL=${_SUPABASE_URL},OPENAI_API_KEY=${_OPENAI_API_KEY}'
      - '--set-secrets=SUPABASE_SERVICE_KEY=supabase-key:latest'
```

### 6. Environment Variables

```bash
# .env.production

# Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_SERVICE_KEY=eyJ...  # Service role key for backend
SUPABASE_ANON_KEY=eyJ...     # Anon key for frontend

# GCP
GCP_PROJECT_ID=your-project-id
GCP_REGION=us-central1

# OpenAI (stored in GCP Secret Manager)
OPENAI_API_KEY=sk-...

# Application
API_URL=https://aiwebimage-api-xxxxx-uc.a.run.app
```

## Cost Comparison

### Previous Architecture (Multiple Services)
- PostgreSQL hosting: $15/month
- Redis: $10/month  
- S3/R2: $5/month
- CDN: $10/month
- Container hosting: $20/month
- **Total: ~$60/month**

### GCP + Supabase Only
- Supabase Free Tier: $0 (or $25/month Pro for more storage)
- Cloud Run: ~$10/month (scales to zero)
- Cloud CDN: ~$5/month
- **Total: ~$15/month (or $40/month with Supabase Pro)**

## Key Advantages

1. **Simplified Infrastructure**
   - Only 2 services to manage
   - Both have generous free tiers
   - Excellent documentation

2. **Built-in Features**
   - pgvector is already enabled in Supabase
   - Authentication included
   - Realtime subscriptions built-in
   - Storage with CDN URLs

3. **Better Developer Experience**
   - Supabase Dashboard for data management
   - GCP Console for monitoring
   - Integrated logging and metrics

4. **Scalability**
   - Cloud Run auto-scales
   - Supabase handles database scaling
   - Cloud CDN for global distribution

## Migration Steps

1. **Set up Supabase Project**
   ```bash
   # Create project at supabase.com
   # Copy connection strings and keys
   ```

2. **Enable pgvector**
   ```sql
   -- Already enabled in Supabase!
   -- Just create your tables
   ```

3. **Deploy to Cloud Run**
   ```bash
   gcloud run deploy aiwebimage-api \
     --source . \
     --region us-central1 \
     --allow-unauthenticated
   ```

4. **Configure CDN**
   ```bash
   # Supabase Storage URLs are already CDN-backed
   # Optionally add Cloud CDN for extra performance
   ```

## Database Functions for Supabase

```sql
-- Create RPC function for vector search
CREATE OR REPLACE FUNCTION search_similar_images(
  query_embedding vector(1536),
  match_threshold float,
  match_count int
)
RETURNS TABLE (
  id uuid,
  url text,
  score float,
  tags text[],
  description text
)
LANGUAGE plpgsql
AS $$
BEGIN
  RETURN QUERY
  SELECT 
    i.id,
    s.url,
    1 - (ie.embedding <=> query_embedding) as score,
    array_agg(it.tag),
    id.description
  FROM images i
  JOIN image_embeddings ie ON i.id = ie.image_id
  JOIN image_variants iv ON i.id = iv.image_id
  JOIN image_descriptions id ON i.id = id.image_id
  LEFT JOIN image_tags it ON i.id = it.image_id
  WHERE 
    i.status = 'approved'
    AND 1 - (ie.embedding <=> query_embedding) > match_threshold
  GROUP BY i.id, s.url, id.description, ie.embedding
  ORDER BY score DESC
  LIMIT match_count;
END;
$$;

-- Enable RLS policies
CREATE POLICY "Public can search images" ON images
  FOR SELECT USING (status = 'approved');

CREATE POLICY "Service role can do everything" ON images
  FOR ALL USING (auth.role() = 'service_role');
```

## Monitoring Setup

```python
# backend/api/monitoring.py
from google.cloud import monitoring_v3
import time

class GCPMonitoring:
    def __init__(self):
        self.client = monitoring_v3.MetricServiceClient()
        self.project = f"projects/{os.getenv('GCP_PROJECT_ID')}"
    
    def track_search(self, latency: float):
        """Send metrics to Cloud Monitoring."""
        series = monitoring_v3.TimeSeries()
        series.metric.type = "custom.googleapis.com/search/latency"
        
        point = monitoring_v3.Point()
        point.value.double_value = latency
        point.interval.end_time.seconds = int(time.time())
        
        series.points = [point]
        self.client.create_time_series(
            name=self.project,
            time_series=[series]
        )
```

## Summary

Using just GCP and Supabase, you get:
- ✅ Managed PostgreSQL with pgvector
- ✅ Built-in authentication
- ✅ Object storage with CDN
- ✅ Serverless compute that scales to zero
- ✅ Global CDN distribution
- ✅ Monitoring and logging
- ✅ Significant cost savings
- ✅ Simpler operations

This architecture is production-ready, cost-effective, and much easier to manage than coordinating multiple services.