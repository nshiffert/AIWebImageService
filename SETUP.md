# Local Development Setup

## Quick Start

### 1. Set up your environment file

```bash
cp backend/.env.example backend/.env
```

Then edit `backend/.env` and add your OpenAI API key:
```
OPENAI_API_KEY=sk-your-actual-api-key-here
```

### 2. Start Docker services

```bash
docker-compose up --build
```

This will:
- Start PostgreSQL with pgvector extension
- Initialize the database with the schema
- Start the FastAPI backend
- Make the API available at http://localhost:8000

### 3. Verify it's working

Open your browser to:
- **API Docs**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### 4. Generate your first test image

```bash
# In a new terminal, run the test script
docker-compose exec api python scripts/test_generation.py
```

This will:
1. Generate an image using DALL-E 3
2. Create 5 size variants
3. Auto-tag with GPT-4 Vision
4. Create embeddings for search
5. Store everything in the database

### 5. Test the search API

```bash
curl -X POST "http://localhost:8000/api/v1/search" \
  -H "X-API-Key: test-key-local-dev-only" \
  -H "Content-Type: application/json" \
  -d '{"query": "chocolate cookies", "limit": 5}'
```

## API Endpoints

### Public Search API
- `POST /api/v1/search` - Search for images
  - Requires `X-API-Key` header
  - For local dev: use `test-key-local-dev-only`

### Admin API (no auth in local dev)
- `POST /api/admin/generate` - Generate single image
- `POST /api/admin/generate/batch` - Generate multiple images
- `GET /api/admin/images/review` - List images pending review
- `POST /api/admin/images/{id}/approve` - Approve an image
- `DELETE /api/admin/images/{id}` - Delete an image
- `GET /api/admin/stats` - Get system statistics

### Health
- `GET /health` - System health check
- `GET /ping` - Simple ping

## Development Workflow

### View logs
```bash
docker-compose logs -f api
docker-compose logs -f postgres
```

### Access database directly
```bash
docker-compose exec postgres psql -U postgres -d aiwebimage
```

### Restart services
```bash
docker-compose restart api
```

### Stop everything
```bash
docker-compose down
```

### Clean database (start fresh)
```bash
docker-compose down -v
docker-compose up --build
```

## Cost Estimates

For local testing:
- **Image Generation**: $0.04-0.08 per image (DALL-E 3 HD)
- **Auto-tagging**: ~$0.012 per image (GPT-4 Vision + GPT-4 Turbo)
- **Search**: ~$0.0001 per query (text-embedding-ada-002)

**Total per image**: ~$0.05-0.10

Budget recommendation for testing: Start with $10 credit (100-200 test images)

## Troubleshooting

### "OpenAI client not initialized"
- Make sure you've copied `.env.example` to `.env`
- Add your OpenAI API key to `backend/.env`
- Restart: `docker-compose restart api`

### "Database connection failed"
- Check postgres is running: `docker-compose ps`
- View logs: `docker-compose logs postgres`
- Try: `docker-compose restart postgres`

### "Port already in use"
- Check if another service is using port 8000 or 5432
- Stop it or change ports in `docker-compose.yml`

### Images not found
- Check storage directory exists: `ls -la volumes/storage/`
- Check database: `docker-compose exec postgres psql -U postgres -d aiwebimage -c "SELECT COUNT(*) FROM images;"`

## Next Steps

1. Generate a few test images
2. Test the search functionality
3. Review the API docs at http://localhost:8000/docs
4. Check the CLAUDE.md file for architecture details
5. Ready to deploy to production? See GCP_Supabase_Deployment.md
