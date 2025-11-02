# AIWebImageService - Complete Setup Runbooks

## Table of Contents
1. [Pre-Claude Code Checklist](#1-pre-claude-code-checklist)
2. [Local Development Setup](#2-local-development-setup)
3. [Production Setup (Supabase)](#3-production-setup-supabase)
4. [Production Setup (GCP)](#4-production-setup-gcp)
5. [CI/CD Setup (GitHub Actions)](#5-cicd-setup-github-actions)
6. [Claude Code Development Workflow](#6-claude-code-development-workflow)
7. [Post-Setup Verification](#7-post-setup-verification)

---

## 1. Pre-Claude Code Checklist

### Accounts & Access Required

#### Essential Accounts
- [ ] **GitHub Account** - Repository created at `nshiffert/AIWebImageService`
- [ ] **Supabase Account** - Free tier is sufficient to start
- [ ] **Google Cloud Platform Account** - With billing enabled
- [ ] **OpenAI Platform Account** - With API access and credits

#### API Keys & Credentials Needed
- [ ] **At least ONE Image Generation Provider:**
  - [ ] **Option A: OpenAI API Key** 
    - DALL-E 3 access ($0.04-0.08 per image)
    - Synchronous (instant results)
    - Best quality, most expensive
  - [ ] **Option B: Leonardo.ai API Key**
    - ~$0.002 per image
    - Asynchronous (webhook callbacks)
    - Good quality, very affordable
  - [ ] **Option C: Runware API Key**
    - ~$0.003 per image
    - Asynchronous (polling required)
    - Fast generation, good quality
- [ ] **OpenAI API Key for Tagging** (required regardless of image provider)
  - [ ] GPT-4 Vision Preview ($0.01 per image analysis)
  - [ ] GPT-4 Turbo ($0.01 per 1K tokens)
  - [ ] Text-Embedding-Ada-002 ($0.0001 per 1K tokens)
- [ ] **GitHub Personal Access Token** (for CI/CD)

#### Local Development Tools
- [ ] **Git** installed and configured
- [ ] **Docker Desktop** installed and running
- [ ] **Node.js 18+** and npm installed
- [ ] **Python 3.11+** installed
- [ ] **Google Cloud SDK** (`gcloud` CLI) installed
- [ ] **Supabase CLI** (optional but helpful)

#### Budget Planning
- [ ] **Image Generation** (choose one or more):
  - OpenAI/DALL-E: ~$40-80 for 1000 images
  - Leonardo.ai: ~$2 for 1000 images  
  - Runware: ~$3 for 1000 images
- [ ] **Tagging/Analysis**: ~$12 for 1000 images (OpenAI required)
- [ ] GCP Free Trial: $300 credits (sufficient for 6+ months)
- [ ] Supabase: Free tier (or $25/month Pro)

---

## 2. Local Development Setup

### Step 1: Repository Setup

```bash
# Clone the repository
git clone https://github.com/nshiffert/AIWebImageService.git
cd AIWebImageService

# Create initial branch structure
git checkout -b develop
git push -u origin develop

# Create .gitignore
cat > .gitignore << 'EOF'
# Environment files
.env
.env.local
.env.production
*.env

# Dependencies
node_modules/
__pycache__/
*.pyc
.venv/
venv/

# IDE
.vscode/
.idea/
*.swp
*.swo
.DS_Store

# Build outputs
build/
dist/
*.egg-info/

# Logs
*.log
logs/

# Local data
postgres_data/
storage_data/
*.db

# Credentials
*.json
*.pem
*.key
service-account.json

# Test coverage
coverage/
.coverage
*.cover
.pytest_cache/

# Docker volumes
volumes/
EOF

git add .gitignore
git commit -m "Add .gitignore"
git push
```

### Step 2: Project Structure Creation

```bash
# Create directory structure
mkdir -p backend/api/{routers,services,models,db}
mkdir -p backend/scripts
mkdir -p frontend/src/{pages,components,services,lib}
mkdir -p frontend/public
mkdir -p .github/workflows
mkdir -p docs
mkdir -p monitoring

# Create placeholder files
touch backend/requirements.txt
touch backend/Dockerfile
touch backend/.env.example
touch frontend/package.json
touch frontend/Dockerfile
touch frontend/.env.example
touch docker-compose.yml
touch README.md
touch ARCHITECTURE.md

# Add architecture document
# Copy the MVP_Architecture_ClaudeCode.md content to ARCHITECTURE.md
```

### Step 3: Docker Compose Setup

```yaml
# docker-compose.yml
version: '3.8'

services:
  # Supabase Local Stack
  postgres:
    image: supabase/postgres:15.1.0.117
    ports:
      - "5432:5432"
    environment:
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: postgres
    volumes:
      - ./volumes/db/data:/var/lib/postgresql/data
      - ./backend/scripts/init.sql:/docker-entrypoint-initdb.d/init.sql
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  supabase-studio:
    image: supabase/studio:latest
    ports:
      - "3001:3000"
    environment:
      STUDIO_PG_META_URL: http://postgres:5432
      POSTGRES_PASSWORD: postgres
    depends_on:
      - postgres
```

### Step 4: Environment Files

```bash
# backend/.env.example
SUPABASE_URL=http://localhost:8000
SUPABASE_SERVICE_KEY=your-local-service-key
OPENAI_API_KEY=sk-...
GCP_PROJECT_ID=your-project-id
ENV=development

# frontend/.env.example
REACT_APP_SUPABASE_URL=http://localhost:8000
REACT_APP_SUPABASE_ANON_KEY=your-local-anon-key
REACT_APP_API_URL=http://localhost:8000
```

### Step 5: Local SSL Setup (Optional)

```bash
# Generate local SSL certificates for HTTPS testing
brew install mkcert  # macOS
mkcert -install
mkcert localhost 127.0.0.1 ::1
mkdir -p .certs
mv localhost+2*.pem .certs/
```

---

## 3. Production Setup (Supabase)

### Step 1: Create Supabase Project

1. **Navigate to** [https://supabase.com](https://supabase.com)
2. **Sign in** with GitHub
3. **Create New Project:**
   - [ ] Project name: `aiwebimageservice`
   - [ ] Database Password: Generate strong password (save in password manager)
   - [ ] Region: Choose closest to your users (e.g., `us-east-1`)
   - [ ] Pricing plan: Free tier (upgrade later if needed)

### Step 2: Configure Supabase

```sql
-- Run in Supabase SQL Editor (Dashboard > SQL Editor)

-- 1. Enable pgvector (already enabled in Supabase)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create storage bucket
INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types) 
VALUES (
  'images', 
  'images', 
  true,
  5242880, -- 5MB limit
  ARRAY['image/jpeg', 'image/png', 'image/webp']
);

-- 3. Create cache table
CREATE TABLE IF NOT EXISTS search_cache (
    cache_key VARCHAR(32) PRIMARY KEY,
    query TEXT NOT NULL,
    size VARCHAR(20),
    results JSONB NOT NULL,
    expires_at TIMESTAMP WITH TIME ZONE NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_cache_expires ON search_cache(expires_at);

-- 4. Run the full schema from ARCHITECTURE.md
-- (Copy the entire schema from Section 4 of ARCHITECTURE.md)
```

### Step 3: Supabase Security Setup

```sql
-- Configure RLS policies
ALTER TABLE images ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_variants ENABLE ROW LEVEL SECURITY;
ALTER TABLE image_tags ENABLE ROW LEVEL SECURITY;

-- Public read for approved images
CREATE POLICY "Public can view approved images" ON images
  FOR SELECT USING (status = 'approved');

-- Service role full access
CREATE POLICY "Service role has full access" ON images
  FOR ALL USING (auth.role() = 'service_role');

-- Storage policies
CREATE POLICY "Public can view images" ON storage.objects
  FOR SELECT USING (bucket_id = 'images');

CREATE POLICY "Service role can upload images" ON storage.objects
  FOR INSERT WITH CHECK (bucket_id = 'images' AND auth.role() = 'service_role');
```

### Step 4: Create Admin User

```javascript
// Run in Supabase Dashboard > Authentication > Users
// Or use Supabase Management API

// Create admin user
const { data, error } = await supabase.auth.admin.createUser({
  email: 'admin@aiwebimageservice.com',
  password: 'your-secure-password',
  email_confirm: true,
  user_metadata: {
    role: 'admin'
  }
})
```

### Step 5: Save Credentials

```bash
# Create secure storage for credentials
mkdir -p ~/.aiwebimageservice
cat > ~/.aiwebimageservice/supabase.env << 'EOF'
SUPABASE_URL=https://xxxxxxxxxxxx.supabase.co
SUPABASE_ANON_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_SERVICE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
SUPABASE_JWT_SECRET=your-jwt-secret
DATABASE_URL=postgresql://postgres:[password]@db.[ref].supabase.co:5432/postgres
EOF

chmod 600 ~/.aiwebimageservice/supabase.env
```

---

## 4. Production Setup (GCP)

### Step 1: Project Setup

```bash
# Create new project
gcloud projects create aiwebimageservice-prod \
  --name="AI Web Image Service" \
  --set-as-default

# Set project
gcloud config set project aiwebimageservice-prod

# Link billing account (required for Cloud Run)
gcloud billing accounts list
gcloud billing projects link aiwebimageservice-prod \
  --billing-account=BILLING_ACCOUNT_ID

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  secretmanager.googleapis.com \
  cloudbuild.googleapis.com \
  containerregistry.googleapis.com \
  cloudscheduler.googleapis.com \
  monitoring.googleapis.com \
  logging.googleapis.com
```

### Step 2: Service Account Setup

```bash
# Create service account for Cloud Run
gcloud iam service-accounts create aiwebimage-runner \
  --display-name="AI Web Image Service Runner"

# Grant necessary permissions
gcloud projects add-iam-policy-binding aiwebimageservice-prod \
  --member="serviceAccount:aiwebimage-runner@aiwebimageservice-prod.iam.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"

gcloud projects add-iam-policy-binding aiwebimageservice-prod \
  --member="serviceAccount:aiwebimage-runner@aiwebimageservice-prod.iam.gserviceaccount.com" \
  --role="roles/logging.logWriter"

gcloud projects add-iam-policy-binding aiwebimageservice-prod \
  --member="serviceAccount:aiwebimage-runner@aiwebimageservice-prod.iam.gserviceaccount.com" \
  --role="roles/monitoring.metricWriter"
```

### Step 3: Secret Manager Setup

```bash
# Store OpenAI credentials (required for tagging/embeddings)
echo -n "sk-..." | gcloud secrets create openai-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Store image generation provider keys (at least one required)
# Option A: OpenAI (if using for image generation)
# Already stored above

# Option B: Leonardo.ai
echo -n "your-leonardo-api-key" | gcloud secrets create leonardo-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Option C: Runware
echo -n "your-runware-api-key" | gcloud secrets create runware-api-key \
  --data-file=- \
  --replication-policy="automatic"

# Store Supabase credentials
echo -n "your-supabase-service-key" | gcloud secrets create supabase-service-key \
  --data-file=- \
  --replication-policy="automatic"

# Store Supabase URL
echo -n "https://xxxxxxxxxxxx.supabase.co" | gcloud secrets create supabase-url \
  --data-file=- \
  --replication-policy="automatic"

# Store webhook secret (for async providers)
echo -n "$(openssl rand -hex 32)" | gcloud secrets create webhook-secret \
  --data-file=- \
  --replication-policy="automatic"

# Grant Cloud Run access to all secrets
for SECRET in supabase-service-key openai-api-key supabase-url webhook-secret leonardo-api-key runware-api-key; do
  gcloud secrets add-iam-policy-binding $SECRET \
    --member="serviceAccount:aiwebimage-runner@aiwebimageservice-prod.iam.gserviceaccount.com" \
    --role="roles/secretmanager.secretAccessor" 2>/dev/null || true
done
```

### Step 4: Container Registry Setup

```bash
# Configure Docker for GCR
gcloud auth configure-docker

# Create Artifact Registry repository (newer, recommended)
gcloud artifacts repositories create aiwebimage \
  --repository-format=docker \
  --location=us-central1 \
  --description="AI Web Image Service containers"
```

### Step 5: Cloud Run Configuration

```bash
# Create Cloud Run service configuration
cat > cloud-run-backend.yaml << 'EOF'
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: aiwebimage-api
  annotations:
    run.googleapis.com/ingress: all
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/minScale: "0"
        autoscaling.knative.dev/maxScale: "10"
        run.googleapis.com/cpu-throttling: "false"
    spec:
      serviceAccountName: aiwebimage-runner@aiwebimageservice-prod.iam.gserviceaccount.com
      containers:
        - image: us-central1-docker.pkg.dev/aiwebimageservice-prod/aiwebimage/backend:latest
          resources:
            limits:
              cpu: "2"
              memory: "2Gi"
          env:
            - name: GCP_PROJECT_ID
              value: aiwebimageservice-prod
            - name: ENV
              value: production
            - name: IMAGE_PROVIDER
              value: leonardo  # or openai, runware
          envFrom:
            - secretRef:
                name: supabase-url
            - secretRef:
                name: supabase-service-key
            - secretRef:
                name: openai-api-key
            - secretRef:
                name: leonardo-api-key  # if using
            - secretRef:
                name: runware-api-key   # if using
            - secretRef:
                name: webhook-secret
EOF
```

### Step 6: Configure Webhooks (for Async Providers)

If using Leonardo.ai or Runware:

```bash
# Get your Cloud Run service URL
SERVICE_URL=$(gcloud run services describe aiwebimage-api \
  --region us-central1 \
  --format 'value(status.url)')

echo "Your webhook URLs:"
echo "Leonardo: ${SERVICE_URL}/api/admin/webhooks/leonardo"
echo "Runware: ${SERVICE_URL}/api/admin/webhooks/runware"

# Configure these webhook URLs in your provider dashboards:
# 
# Leonardo.ai:
# 1. Go to https://app.leonardo.ai/settings/api
# 2. Set webhook URL to: ${SERVICE_URL}/api/admin/webhooks/leonardo
# 
# Runware:
# 1. Go to https://runware.ai/dashboard/webhooks
# 2. Add webhook endpoint: ${SERVICE_URL}/api/admin/webhooks/runware
```

---

## 5. CI/CD Setup (GitHub Actions)

### Step 1: GitHub Secrets Configuration

Navigate to GitHub repository > Settings > Secrets and variables > Actions

Add the following secrets:
- [ ] `GCP_PROJECT_ID` - Your GCP project ID
- [ ] `GCP_SA_KEY` - Service account JSON key (base64 encoded)
- [ ] `SUPABASE_URL` - Production Supabase URL
- [ ] `SUPABASE_SERVICE_KEY` - Production service key
- [ ] `SUPABASE_ANON_KEY` - Production anon key
- [ ] `OPENAI_API_KEY` - OpenAI API key

```bash
# Create and encode service account key
gcloud iam service-accounts keys create sa-key.json \
  --iam-account=aiwebimage-runner@aiwebimageservice-prod.iam.gserviceaccount.com

base64 sa-key.json | pbcopy  # macOS
# base64 sa-key.json | xclip  # Linux
# Then paste into GitHub secret GCP_SA_KEY

rm sa-key.json  # Delete local copy
```

### Step 2: GitHub Actions Workflow

```yaml
# .github/workflows/deploy-production.yml
name: Deploy to Production

on:
  push:
    branches: [main]
  workflow_dispatch:

env:
  GCP_PROJECT_ID: ${{ secrets.GCP_PROJECT_ID }}
  GCP_REGION: us-central1
  SERVICE_NAME: aiwebimage-api

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        working-directory: ./backend
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Run tests
        working-directory: ./backend
        env:
          SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          SUPABASE_SERVICE_KEY: ${{ secrets.SUPABASE_SERVICE_KEY }}
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}
        run: |
          pytest tests/ --cov=api --cov-report=xml
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
        with:
          file: ./backend/coverage.xml

  deploy-backend:
    needs: test
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    
    steps:
      - uses: actions/checkout@v3
      
      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Set up Cloud SDK
        uses: google-github-actions/setup-gcloud@v1
      
      - name: Configure Docker
        run: |
          gcloud auth configure-docker us-central1-docker.pkg.dev
      
      - name: Build and Push Container
        working-directory: ./backend
        run: |
          docker build -t us-central1-docker.pkg.dev/$GCP_PROJECT_ID/aiwebimage/backend:$GITHUB_SHA .
          docker tag us-central1-docker.pkg.dev/$GCP_PROJECT_ID/aiwebimage/backend:$GITHUB_SHA \
                     us-central1-docker.pkg.dev/$GCP_PROJECT_ID/aiwebimage/backend:latest
          docker push us-central1-docker.pkg.dev/$GCP_PROJECT_ID/aiwebimage/backend:$GITHUB_SHA
          docker push us-central1-docker.pkg.dev/$GCP_PROJECT_ID/aiwebimage/backend:latest
      
      - name: Deploy to Cloud Run
        run: |
          gcloud run deploy $SERVICE_NAME \
            --image us-central1-docker.pkg.dev/$GCP_PROJECT_ID/aiwebimage/backend:$GITHUB_SHA \
            --region $GCP_REGION \
            --platform managed \
            --allow-unauthenticated \
            --service-account aiwebimage-runner@$GCP_PROJECT_ID.iam.gserviceaccount.com \
            --set-secrets="SUPABASE_URL=supabase-url:latest,SUPABASE_SERVICE_KEY=supabase-service-key:latest,OPENAI_API_KEY=openai-api-key:latest" \
            --set-env-vars="GCP_PROJECT_ID=$GCP_PROJECT_ID,ENV=production"
      
      - name: Get Service URL
        run: |
          echo "SERVICE_URL=$(gcloud run services describe $SERVICE_NAME --region $GCP_REGION --format 'value(status.url)')" >> $GITHUB_ENV
      
      - name: Smoke Test
        run: |
          curl -f ${{ env.SERVICE_URL }}/health || exit 1

  deploy-frontend:
    needs: test
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Setup Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'
          cache-dependency-path: frontend/package-lock.json
      
      - name: Install dependencies
        working-directory: ./frontend
        run: npm ci
      
      - name: Build frontend
        working-directory: ./frontend
        env:
          REACT_APP_SUPABASE_URL: ${{ secrets.SUPABASE_URL }}
          REACT_APP_SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}
          REACT_APP_API_URL: https://aiwebimage-api-xxxxx-uc.a.run.app
        run: npm run build
      
      - id: auth
        uses: google-github-actions/auth@v1
        with:
          credentials_json: ${{ secrets.GCP_SA_KEY }}
      
      - name: Deploy to Firebase Hosting
        uses: FirebaseExtended/action-hosting-deploy@v0
        with:
          repoToken: ${{ secrets.GITHUB_TOKEN }}
          firebaseServiceAccount: ${{ secrets.GCP_SA_KEY }}
          channelId: live
          projectId: ${{ secrets.GCP_PROJECT_ID }}
```

### Step 3: Development Workflow

```yaml
# .github/workflows/deploy-development.yml
name: Deploy to Development

on:
  push:
    branches: [develop]
  pull_request:
    branches: [main]

jobs:
  test-and-preview:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run linting
        working-directory: ./backend
        run: |
          pip install flake8 black
          black --check .
          flake8 .
      
      - name: Run frontend tests
        working-directory: ./frontend
        run: |
          npm ci
          npm test -- --coverage --watchAll=false
      
      - name: Build preview
        if: github.event_name == 'pull_request'
        run: echo "Would deploy preview to Cloud Run"
```

---

## 6. Claude Code Development Workflow

### Initial Setup Instructions for Claude Code

```markdown
# Instructions for Claude Code

## Project Overview
You are building AIWebImageService, a vector-searchable image library for cottage food businesses.

## Repository
- GitHub: https://github.com/nshiffert/AIWebImageService
- Branch: develop (create feature branches from here)

## Architecture
- Refer to ARCHITECTURE.md for complete technical specifications
- Stack: FastAPI (backend), React (frontend), Supabase (database/storage), GCP (hosting)

## Development Workflow

### 1. Initial Setup
```bash
git clone https://github.com/nshiffert/AIWebImageService.git
cd AIWebImageService
git checkout develop
```

### 2. Backend Development
- Start with backend/api/main.py
- Implement services in order: config.py, database.py, auth.py, generator.py, tagger.py
- Create API routes in routers/
- Write tests in backend/tests/

### 3. Frontend Development
- Initialize React app with TypeScript
- Set up Supabase client in lib/supabase.ts
- Create pages in order: Login, Dashboard, Generate, Review, Library
- Implement components as needed

### 4. Testing
- Run backend tests: `pytest backend/tests/`
- Run frontend tests: `npm test`
- Test locally with docker-compose

### 5. Git Workflow
- Create feature branches: `git checkout -b feature/description`
- Commit frequently with clear messages
- Push to origin and create PR to develop
- After review, merge to develop
- Deploy to production by merging develop to main

## Environment Variables
Check .env.example files for required variables.

## Key Files to Create First
1. backend/api/main.py - FastAPI app initialization
2. backend/api/config.py - Configuration and Supabase client
3. backend/api/db/models.py - Database models
4. frontend/src/lib/supabase.ts - Supabase client
5. docker-compose.yml - Local development setup

## Testing Checklist
- [ ] API health endpoint works
- [ ] Supabase connection successful
- [ ] Image generation creates all sizes
- [ ] Auto-tagging produces valid tags
- [ ] Vector search returns results
- [ ] Frontend authentication works
- [ ] Admin can approve images
```

### Development Commands Cheatsheet

```bash
# Backend Development
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn api.main:app --reload

# Frontend Development
cd frontend
npm install
npm start

# Docker Development
docker-compose up -d
docker-compose logs -f
docker-compose down

# Database Migrations
docker-compose exec postgres psql -U postgres -d postgres -f /scripts/schema.sql

# Testing
# Backend
pytest backend/tests/ -v
pytest backend/tests/ --cov=api

# Frontend
npm test
npm run test:coverage

# Linting
black backend/
flake8 backend/
npm run lint

# Building
docker build -t aiwebimage-backend backend/
docker build -t aiwebimage-frontend frontend/

# Git Workflow
git checkout develop
git pull origin develop
git checkout -b feature/my-feature
# Make changes
git add .
git commit -m "feat: add new feature"
git push origin feature/my-feature
# Create PR on GitHub

# Deployment (automatic via GitHub Actions)
# Merge to main triggers production deployment
```

---

## 7. Post-Setup Verification

### Local Development Verification

```bash
# 1. Database Check
docker-compose exec postgres psql -U postgres -c "\dt"
# Should show all tables

# 2. API Health Check
curl http://localhost:8000/health
# Should return {"status": "healthy"}

# 3. Frontend Check
curl http://localhost:3000
# Should return React app HTML

# 4. Supabase Studio
open http://localhost:3001
# Should show Supabase dashboard
```

### Production Verification

```bash
# 1. Cloud Run Service
gcloud run services describe aiwebimage-api --region us-central1
# Should show service details

# 2. API Health Check
curl https://aiwebimage-api-xxxxx-uc.a.run.app/health
# Should return {"status": "healthy"}

# 3. Supabase Connection
curl -X POST https://aiwebimage-api-xxxxx-uc.a.run.app/api/v1/test-db
# Should return {"connected": true}

# 4. Secret Manager
gcloud secrets list
# Should show all secrets

# 5. Monitoring
gcloud monitoring dashboards list
# Should show dashboards
```

### Initial Data Seeding

```python
# scripts/seed_initial_data.py
import asyncio
from api.services.generator import ImageGenerator
from api.config import supabase

async def seed_data():
    """Generate initial images for testing."""
    
    generator = ImageGenerator()
    
    test_prompts = [
        "chocolate chip cookies on white plate",
        "rustic sourdough bread on cutting board",
        "decorated birthday cake on cake stand",
        "jar of strawberry jam with label",
        "fresh croissants in basket"
    ]
    
    for prompt in test_prompts:
        print(f"Generating: {prompt}")
        try:
            # Generate image
            image_bytes = await generator.generate_image(prompt)
            
            # Create variants
            variants = generator.create_variants(image_bytes)
            
            # Upload and save
            # ... implementation
            
            print(f"✓ Generated and saved: {prompt}")
        except Exception as e:
            print(f"✗ Failed: {prompt} - {e}")

if __name__ == "__main__":
    asyncio.run(seed_data())
```

### Performance Benchmarks

```bash
# Test search performance
time curl -X POST https://aiwebimage-api-xxxxx-uc.a.run.app/api/v1/search \
  -H "X-API-Key: test-key" \
  -H "Content-Type: application/json" \
  -d '{"query": "chocolate chip cookies", "limit": 5}'

# Should return in < 100ms

# Test generation (admin only)
curl -X POST https://aiwebimage-api-xxxxx-uc.a.run.app/api/admin/generate \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"prompt": "test cookie", "count": 1}'

# Should complete in < 30s
```

---

## Summary

### Critical Path for Claude Code

1. **Fork/Clone Repository** → Set up local development
2. **Create Supabase Project** → Get credentials
3. **Set up GCP Project** → Configure Cloud Run
4. **Add GitHub Secrets** → Enable CI/CD
5. **Create Initial Schema** → Database ready
6. **Implement Backend** → API functional
7. **Implement Frontend** → UI complete
8. **Write Tests** → Ensure quality
9. **Deploy to Production** → Go live

### Time Estimates

- **Pre-setup (accounts, credentials)**: 2-3 hours
- **Supabase configuration**: 1 hour
- **GCP configuration**: 2 hours
- **GitHub Actions setup**: 1 hour
- **Claude Code implementation**: 8-12 hours
- **Testing and debugging**: 2-4 hours
- **Initial data seeding**: 1-2 hours
- **Total**: ~20-25 hours

### Cost Estimates (Monthly)

- **Development Phase**:
  - Supabase: $0 (free tier)
  - GCP: $0 (using free trial credits)
  - Image Generation Testing:
    - With OpenAI: ~$40-50
    - With Leonardo: ~$2-5
    - With Runware: ~$3-5
  - Tagging/Embeddings: ~$10 (OpenAI required)

- **Production (after launch)**:
  - Supabase: $0-25
  - GCP Cloud Run: $10-20
  - New images per month (100 images):
    - With OpenAI: $4-8 + $1.20 tagging
    - With Leonardo: $0.20 + $1.20 tagging  
    - With Runware: $0.30 + $1.20 tagging
  - **Total**: $15-55/month depending on provider choice

### Provider Comparison

| Provider | Cost/Image | Speed | Quality | Integration |
|----------|-----------|-------|---------|-------------|
| OpenAI | $0.04-0.08 | Instant | Excellent | Synchronous |
| Leonardo | $0.002 | 20-30s | Very Good | Webhooks |
| Runware | $0.003 | 15-25s | Good | Polling/Webhooks |

**Recommendation**: Start with Leonardo or Runware for cost efficiency during development, keep OpenAI as premium option.

This completes all the runbooks needed to set up and deploy AIWebImageService!