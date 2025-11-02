# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AIWebImageService is an AI-powered, vector-searchable image library designed for cottage food business websites. It provides a read-only API for finding images based on text queries, with image generation and management handled through an admin panel.

**Core Value Proposition**: Generate once, use everywhere - shared image library that serves thousands of cottage food websites cost-effectively.

## Tech Stack

### Backend
- **FastAPI** (Python 3.11+) - API server
- **Supabase** - PostgreSQL with pgvector (pre-enabled), Auth, Storage, Realtime
- **OpenAI APIs** - Required for tagging/embeddings (GPT-4 Vision, Text-Embedding-Ada-002)
- **Image Generation** - Multiple provider support:
  - OpenAI DALL-E 3 (synchronous, $0.04-0.08/image)
  - Leonardo.ai (async with webhooks, ~$0.002/image)
  - Runware (async with polling, ~$0.003/image)

### Frontend
- **React 18** with TypeScript
- **Supabase JS Client** - Authentication and real-time subscriptions
- **TailwindCSS** - Styling
- **React Query** - Data fetching
- **React Hook Form** - Form management

### Infrastructure
- **Google Cloud Run** - Serverless backend hosting (scales to zero)
- **Google Cloud CDN** - Global image delivery
- **Google Secret Manager** - API keys and credentials
- **Supabase Storage** - Image storage with built-in CDN

## Development Commands

### Local Development Setup
```bash
# Start local Supabase and services
docker-compose up -d

# Backend development
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Frontend development
cd frontend
npm install
npm start

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Testing
```bash
# Backend tests
cd backend
pytest tests/ -v
pytest tests/ --cov=api --cov-report=html

# Frontend tests
cd frontend
npm test
npm run test:coverage

# Linting and formatting
cd backend
black .
flake8 .

cd frontend
npm run lint
```

### Database Operations
```bash
# Access local Supabase Studio
open http://localhost:3001

# Run SQL migrations
docker-compose exec postgres psql -U postgres -d postgres

# Check database connection
docker-compose exec api python -c "from api.config import supabase; print(supabase.table('images').select('*').limit(1).execute())"
```

## Architecture Overview

### Service Flow
1. **Admin generates images** → FastAPI backend → Image provider (OpenAI/Leonardo/Runware)
2. **Image processing** → Create 5 size variants → Upload to Supabase Storage
3. **Auto-tagging** → GPT-4 Vision analyzes → Generates searchable tags
4. **Embedding creation** → Text-Embedding-Ada-002 → Store in pgvector
5. **Admin approval** → Image becomes searchable
6. **Client searches** → Vector similarity search → Return CDN URLs

### Image Size Presets
- `thumbnail` - 150×150 (grid views)
- `product_card` - 400×300 (product cards)
- `full_product` - 800×600 (product pages)
- `hero_image` - 1920×600 (page headers)
- `full_res` - 2048×2048 (original quality)

### Database Schema Structure

**Core Tables**:
- `images` - Master image records with generation metadata
- `image_variants` - Size variants with Supabase Storage URLs
- `image_tags` - Searchable tags (auto-generated and manual)
- `image_embeddings` - Vector embeddings for similarity search (pgvector)
- `image_descriptions` - AI-generated descriptions
- `image_colors` - Extracted color palettes
- `generation_jobs` - Track async generation status
- `api_keys` - API authentication for search endpoint
- `search_cache` - Cache search results (optional optimization)

**Key RLS Policies**:
- Public can SELECT approved images only
- Service role has full access
- Authenticated users can manage own images

### Provider Abstraction Pattern

The system uses a provider interface pattern for image generation:

```python
# backend/api/services/providers/base.py
class ImageProviderBase(ABC):
    @abstractmethod
    async def generate(self, prompt: str, width: int, height: int, callback_url: Optional[str]) -> Dict[str, Any]

    @abstractmethod
    async def check_status(self, job_id: str) -> Dict[str, Any]

    @abstractmethod
    def is_async(self) -> bool

    @abstractmethod
    def get_cost_estimate(self, width: int, height: int) -> float
```

Implementations:
- `OpenAIProvider` - Synchronous, returns image immediately
- `LeonardoProvider` - Asynchronous, requires webhook/polling
- `RunwareProvider` - Asynchronous, requires polling

### Key Service Modules

**backend/api/services/**:
- `generator.py` - Image generation orchestration with multi-provider support
- `tagger.py` - GPT-4 Vision auto-tagging
- `embeddings.py` - Text embedding creation
- `storage.py` - Supabase Storage operations
- `database.py` - Database operations using Supabase client
- `auth.py` - Supabase Auth integration
- `cache.py` - Search result caching (optional)

### API Endpoints

**Public Search API** (`/api/v1/search`):
- POST with `X-API-Key` header
- Request: `{query, size, limit, min_score}`
- Returns: Matched images with CDN URLs for requested size
- Uses pgvector cosine similarity search

**Admin API** (`/api/admin/*`):
- Requires Supabase Auth token
- `/generate/batch` - Start batch generation (supports async providers)
- `/generate/status/{job_id}` - Check async generation status
- `/webhooks/{provider}` - Receive provider webhooks
- `/images/{id}/approve` - Approve image for search
- `/images/review` - List pending images
- `/providers` - List available generation providers

## Key Implementation Details

### Supabase Integration

**Config Setup** (`backend/api/config.py`):
```python
from supabase import create_client
import os

supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)
```

**Vector Search** (uses Supabase RPC function):
```python
response = supabase.rpc(
    'search_similar_images',
    {
        'query_embedding': embedding_vector,
        'match_threshold': 0.7,
        'match_count': 10,
        'size_preset': 'product_card'
    }
).execute()
```

**Storage Upload**:
```python
supabase.storage.from_('images').upload(
    path=f"{image_id}/{size}.jpg",
    file=image_bytes,
    file_options={"content-type": "image/jpeg"}
)
```

### Async Provider Handling

For Leonardo.ai and Runware, the system:
1. Submits generation request → Receives job ID
2. Stores job in `generation_jobs` table
3. Either:
   - Receives webhook callback → Process image
   - Polls status endpoint → Download when complete
4. Continues with tagging and approval workflow

**Frontend polling example** (`frontend/src/pages/Generate.tsx`):
```typescript
useEffect(() => {
  if (asyncJobId) {
    const interval = setInterval(async () => {
      const status = await checkJobStatus(asyncJobId);
      if (status.status === 'completed') {
        setAsyncJobId(null);
        toast.success('Generation complete!');
      }
    }, 2000);
    return () => clearInterval(interval);
  }
}, [asyncJobId]);
```

### Environment Variables

**Backend** (`backend/.env`):
```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_SERVICE_KEY=eyJ...

# Google Cloud
GCP_PROJECT_ID=aiwebimageservice-prod
GCP_REGION=us-central1

# Image Generation Provider (choose one or more)
IMAGE_PROVIDER=leonardo  # openai, leonardo, runware

# OpenAI (required for tagging/embeddings)
OPENAI_API_KEY=sk-...

# Optional provider keys
LEONARDO_API_KEY=...
RUNWARE_API_KEY=...

# Webhooks (for async providers)
WEBHOOK_BASE_URL=https://your-api.run.app
WEBHOOK_SECRET=...

# Settings
ENV=development  # or production
AUTO_TAG_ENABLED=true
MIN_TAG_CONFIDENCE=0.7
```

**Frontend** (`frontend/.env`):
```bash
REACT_APP_SUPABASE_URL=https://xxxxx.supabase.co
REACT_APP_SUPABASE_ANON_KEY=eyJ...
REACT_APP_API_URL=http://localhost:8000  # or Cloud Run URL
REACT_APP_ENABLE_PROVIDER_SELECTION=true
```

## Deployment

### Google Cloud Run Deployment
```bash
# Build and deploy backend
cd backend
gcloud builds submit --tag gcr.io/PROJECT_ID/aiwebimage-api
gcloud run deploy aiwebimage-api \
  --image gcr.io/PROJECT_ID/aiwebimage-api \
  --region us-central1 \
  --allow-unauthenticated \
  --set-secrets="SUPABASE_SERVICE_KEY=supabase-service-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
  --set-env-vars="SUPABASE_URL=https://xxxxx.supabase.co,GCP_PROJECT_ID=PROJECT_ID,IMAGE_PROVIDER=leonardo"

# Frontend deployment (Cloud Run or Firebase Hosting)
cd frontend
npm run build
gcloud run deploy aiwebimage-frontend \
  --image gcr.io/PROJECT_ID/aiwebimage-frontend \
  --region us-central1 \
  --allow-unauthenticated
```

### CI/CD via GitHub Actions
- Push to `develop` branch → Runs tests
- Push to `main` branch → Deploys to production
- See `.github/workflows/deploy-production.yml`

## Cost Optimization

### Image Generation Strategy
- **Development/Testing**: Use Leonardo.ai or Runware (~$2-3 per 1000 images)
- **Premium Quality**: Use OpenAI DALL-E 3 (~$40-80 per 1000 images)
- **Hybrid Approach**: Mix providers based on quality requirements

### Infrastructure Costs
- Supabase Free Tier: Sufficient for development and small production
- Cloud Run: Scales to zero, only pay for requests (~$10-20/month typical)
- Total Monthly: $15-55 depending on usage and provider choice

## Common Development Patterns

### Adding a New Image Generation Provider
1. Create provider class in `backend/api/services/providers/`
2. Implement `ImageProviderBase` interface
3. Add provider configuration to `ImageGenerator._get_provider()`
4. Update environment variables and secrets
5. Add webhook endpoint if async: `/api/admin/webhooks/{provider}`

### Adding a New Image Size
1. Update `sizes` dict in `generator.py:create_variants()`
2. Add size to database enum if strict validation needed
3. Update API documentation
4. Update frontend size selector

### Custom Tag Generation
Override tags in admin UI or modify `tagger.py` prompt for domain-specific terminology.

## Important Constraints

- pgvector is **pre-enabled** in Supabase - no manual extension setup needed
- Image generation requires **at least one provider** configured (OpenAI, Leonardo, or Runware)
- OpenAI API key is **always required** for tagging and embeddings (GPT-4 Vision, Ada-002)
- Async providers (Leonardo, Runware) require webhook URLs configured in provider dashboards
- Cloud Run URLs needed for webhook callbacks - deploy backend first
- Row Level Security (RLS) policies must be configured for production security
- Service role key should only be used server-side, never in frontend code

## Security Considerations

- Store service role keys in Google Secret Manager, never in code
- Use Supabase anon key in frontend (RLS protects data)
- Validate webhooks using `WEBHOOK_SECRET` to prevent unauthorized calls
- API keys for search endpoint stored as SHA-256 hashes
- Rate limit search API in production (default: 100 req/min)

## Troubleshooting

### Local Development Issues
- **Database connection fails**: Check `docker-compose ps`, restart postgres container
- **API 500 errors**: Check `docker-compose logs api` for Python errors
- **Frontend auth fails**: Verify `REACT_APP_SUPABASE_URL` and `REACT_APP_SUPABASE_ANON_KEY`

### Production Issues
- **Vector search slow**: Check pgvector index with `EXPLAIN ANALYZE`, may need to adjust `lists` parameter
- **Image generation timeout**: Increase Cloud Run timeout (`--timeout=300`)
- **Webhook not received**: Verify webhook URL in provider dashboard, check Cloud Run logs
- **Storage quota exceeded**: Upgrade Supabase plan or implement image cleanup policy

### Provider-Specific Issues
- **OpenAI rate limit**: Implement request queuing or switch to async provider
- **Leonardo webhook fails**: Verify webhook URL uses HTTPS, check webhook secret
- **Runware polling**: Implement exponential backoff to avoid rate limiting

## Testing Strategy

### Unit Tests
- Service layer functions (generation, tagging, embeddings)
- Database operations (CRUD, vector search)
- Provider implementations

### Integration Tests
- End-to-end image generation workflow
- Search API with real embeddings
- Frontend authentication flow

### Performance Tests
- Vector search latency (target: <100ms p95)
- Image generation throughput
- CDN cache hit rate

## Additional Resources

- **README.md** - Project overview and quick start
- **MVP_Architecture_ClaudeCode.md** - Detailed technical architecture
- **GCP_Supabase_Deployment.md** - Infrastructure setup guide
- **AIWebImageService_Complete_Runbooks.md** - Step-by-step setup procedures
- **Supabase Docs** - https://supabase.com/docs
- **Google Cloud Run Docs** - https://cloud.google.com/run/docs
