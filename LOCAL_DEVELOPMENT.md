# Local Development Guide

## Port Configuration

For consistent local development, the following ports are used:

| Service | Port | URL | Notes |
|---------|------|-----|-------|
| **Frontend** | 3000 | http://localhost:3000 | React app (Vite dev server) |
| **Backend API** | 8000 | http://localhost:8000 | FastAPI application |
| **PostgreSQL** | 5432 | localhost:5432 | Database with pgvector |

## Quick Start

### 1. Start Backend Services

```bash
# From project root
docker-compose up -d

# Check services are running
docker-compose ps

# View logs
docker-compose logs -f api
```

### 2. Start Frontend

```bash
cd frontend
npm install  # First time only
npm run dev
```

The frontend will be available at: **http://localhost:3000**

### 3. Verify Services

- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

## Environment Configuration

### Backend (.env in backend/)

```env
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/aiwebimage
OPENAI_API_KEY=your-key-here
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### Frontend (.env in frontend/)

```env
VITE_API_URL=http://localhost:8000
VITE_API_KEY=test-key-local-dev-only
```

## Stopping Services

```bash
# Stop backend
docker-compose down

# Frontend stops when you Ctrl+C the npm process
```

## Troubleshooting

### CORS Errors

If you see CORS errors:
1. Verify backend CORS_ORIGINS includes `http://localhost:3000`
2. Restart the backend: `docker-compose restart api`

### Port Already in Use

If port 3000 is in use:
```bash
# Find process using port 3000
lsof -ti:3000

# Kill it
kill -9 $(lsof -ti:3000)
```

### Database Connection Issues

```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Restart database
docker-compose restart postgres
```

### Frontend Not Connecting to Backend

1. Check backend is running: `curl http://localhost:8000/health`
2. Check .env files have correct URLs
3. Check browser console for errors
4. Verify CORS settings in backend/.env

## Default Credentials

For local development:
- **Admin Username**: admin
- **Admin Password**: admin

## Development Workflow

1. Make code changes
2. Backend auto-reloads (uvicorn --reload)
3. Frontend auto-reloads (Vite HMR)
4. No need to restart services for code changes
5. Restart only needed for environment variable changes
