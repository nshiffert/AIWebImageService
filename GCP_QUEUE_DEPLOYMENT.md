# GCP Cloud Tasks Queue System Deployment Guide

## Overview

This guide explains how to deploy AIWebImageService to Google Cloud Platform with Cloud Tasks for scalable batch image generation.

## Architecture

### Local Development
- Queue Service uses **controlled concurrency** (max 5 concurrent HTTP requests)
- Worker endpoint processes tasks via direct HTTP calls
- Jobs tracked in PostgreSQL database

### Production (GCP)
- Queue Service uses **Cloud Tasks** for reliable task queuing
- Cloud Run handles worker endpoint with auto-scaling
- Supabase for PostgreSQL + Storage
- Automatic retry logic for failed tasks

## Prerequisites

- GCP Project with billing enabled
- gcloud CLI installed and authenticated
- Supabase project (or PostgreSQL + pgvector)
- OpenAI API key

## Environment Variables

### Backend `.env` (Production)

```bash
# Environment
ENVIRONMENT=production
USE_CLOUD_TASKS=true

# GCP Configuration
GCP_PROJECT=your-gcp-project-id
GCP_LOCATION=us-central1
QUEUE_NAME=image-generation
CLOUD_TASKS_SERVICE_ACCOUNT=image-worker@your-project.iam.gserviceaccount.com

# Worker URL (Cloud Run)
WORKER_URL=https://your-api-service-xxxx-uc.a.run.app/api/admin/worker/process-task

# Database (Supabase)
DATABASE_URL=postgresql://user:pass@db.supabase.co:5432/postgres

# Storage (Supabase)
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
SUPABASE_BUCKET=generated-images

# OpenAI
OPENAI_API_KEY=sk-...

# CORS
CORS_ORIGINS=["https://your-frontend.vercel.app"]
```

## Step-by-Step Deployment

### 1. Setup Supabase Database

```bash
# Run migration SQL
psql $DATABASE_URL -f backend/scripts/init_db.sql
```

### 2. Create Cloud Tasks Queue

```bash
# Create queue
gcloud tasks queues create image-generation \
  --location=us-central1 \
  --max-dispatches-per-second=10 \
  --max-concurrent-dispatches=100

# Verify queue
gcloud tasks queues describe image-generation --location=us-central1
```

### 3. Create Service Account for Cloud Tasks

```bash
# Create service account
gcloud iam service-accounts create image-worker \
  --display-name="Image Generation Worker"

# Grant Cloud Run Invoker role (so Cloud Tasks can call the worker endpoint)
gcloud run services add-iam-policy-binding your-api-service \
  --region=us-central1 \
  --member=serviceAccount:image-worker@your-project.iam.gserviceaccount.com \
  --role=roles/run.invoker
```

### 4. Deploy Backend to Cloud Run

```bash
# Build and deploy
cd backend
gcloud run deploy aiwebimage-api \
  --source . \
  --region=us-central1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --timeout=300s \
  --max-instances=10 \
  --set-env-vars="ENVIRONMENT=production,USE_CLOUD_TASKS=true,GCP_PROJECT=your-project-id"

# Get the service URL
gcloud run services describe aiwebimage-api --region=us-central1 --format='value(status.url)'
```

### 5. Update Environment Variables

Update `WORKER_URL` in Cloud Run with the deployed URL:

```bash
gcloud run services update aiwebimage-api \
  --region=us-central1 \
  --set-env-vars="WORKER_URL=https://aiwebimage-api-xxxx-uc.a.run.app/api/admin/worker/process-task"
```

### 6. Deploy Frontend to Vercel

```bash
cd frontend

# Set environment variables in Vercel
# VITE_API_URL=https://aiwebimage-api-xxxx-uc.a.run.app
# VITE_API_KEY=your-production-api-key

vercel --prod
```

## Testing the Queue System

### Test Batch Generation

```bash
curl -X POST https://your-api.run.app/api/admin/generate/batch \
  -H "Content-Type: application/json" \
  -d '{
    "prompts": ["chocolate cookies", "vanilla cupcakes"],
    "style": "product_photography",
    "count_per_prompt": 1
  }'
```

**Response**:
```json
{
  "id": "job-uuid",
  "status": "pending",
  "total_tasks": 2,
  "completed_tasks": 0,
  "failed_tasks": 0
}
```

### Poll Job Status

```bash
curl https://your-api.run.app/api/admin/jobs/{job_id}/status
```

**Response**:
```json
{
  "id": "job-uuid",
  "status": "running",
  "total_tasks": 2,
  "completed_tasks": 1,
  "failed_tasks": 0,
  "progress_percentage": 50.0
}
```

## Monitoring

### View Cloud Tasks Queue

```bash
# List tasks in queue
gcloud tasks list --queue=image-generation --location=us-central1

# View queue stats
gcloud tasks queues describe image-generation --location=us-central1
```

### View Cloud Run Logs

```bash
# Stream logs
gcloud run services logs tail aiwebimage-api --region=us-central1

# Filter for worker endpoint
gcloud run services logs read aiwebimage-api \
  --region=us-central1 \
  --filter="resource.labels.service_name=aiwebimage-api AND textPayload:worker"
```

### Database Monitoring

```sql
-- Check job status
SELECT status, COUNT(*) FROM generation_jobs GROUP BY status;

-- View active jobs
SELECT id, status, total_tasks, completed_tasks, failed_tasks, created_at
FROM generation_jobs
WHERE status IN ('pending', 'running')
ORDER BY created_at DESC;

-- View task breakdown for a job
SELECT status, COUNT(*) FROM generation_tasks
WHERE job_id = 'your-job-uuid'
GROUP BY status;
```

## Configuration Tuning

### Cloud Tasks Queue Settings

```bash
# Increase concurrent tasks
gcloud tasks queues update image-generation \
  --location=us-central1 \
  --max-concurrent-dispatches=200

# Adjust dispatch rate
gcloud tasks queues update image-generation \
  --location=us-central1 \
  --max-dispatches-per-second=20
```

### Cloud Run Scaling

```bash
# Increase max instances
gcloud run services update aiwebimage-api \
  --region=us-central1 \
  --max-instances=50

# Set min instances (reduces cold starts)
gcloud run services update aiwebimage-api \
  --region=us-central1 \
  --min-instances=1
```

## Cost Estimation

### Cloud Tasks
- **Free tier**: 1M operations/month
- **Paid**: $0.40 per million operations

### Cloud Run
- **CPU**: $0.00002400 per vCPU-second
- **Memory**: $0.00000250 per GiB-second
- **Requests**: $0.40 per million requests

**Example**: 1000 images/month
- 1000 tasks × 80 seconds average = 80,000 seconds
- 2 vCPU × 80,000 = 160,000 vCPU-seconds × $0.000024 = **$3.84/month**
- 2 GB × 80,000 = 160,000 GB-seconds × $0.0000025 = **$0.40/month**
- Cloud Tasks: 1000 operations = **Free**
- **Total**: ~$4.24/month (plus OpenAI costs)

## Troubleshooting

### Tasks Not Processing

1. Check Cloud Tasks queue status:
   ```bash
   gcloud tasks queues describe image-generation --location=us-central1
   ```

2. Verify service account permissions:
   ```bash
   gcloud run services get-iam-policy aiwebimage-api --region=us-central1
   ```

3. Check worker endpoint logs for errors

### High Failure Rate

1. Check OpenAI API quotas
2. Verify database connection pooling
3. Review task retry count in database
4. Increase Cloud Run timeout if needed

### Slow Processing

1. Increase `max-concurrent-dispatches` in Cloud Tasks
2. Increase Cloud Run `max-instances`
3. Monitor OpenAI API rate limits
4. Consider regional deployment for lower latency

## Security Best Practices

1. **Never commit `.env` files** - Use Cloud Run secrets or environment variables
2. **Restrict API keys** - Use separate keys for production
3. **Enable authentication** - Protect admin endpoints with proper auth
4. **Use HTTPS only** - Cloud Run enforces this by default
5. **Rotate service account keys** regularly
6. **Monitor costs** - Set up billing alerts

## Rollback Plan

If deployment fails:

```bash
# Rollback Cloud Run
gcloud run services update-traffic aiwebimage-api \
  --region=us-central1 \
  --to-revisions=PREVIOUS_REVISION=100

# Pause Cloud Tasks queue
gcloud tasks queues pause image-generation --location=us-central1

# Resume after fixing
gcloud tasks queues resume image-generation --location=us-central1
```

## Support

For issues:
1. Check Cloud Run logs
2. Verify Cloud Tasks queue status
3. Test worker endpoint directly
4. Review database job/task status
5. Check OpenAI API status

---

**Ready for Production!**

The queue system is designed to handle massive batches (200+ images) without timeouts, with automatic retry logic and real-time progress tracking.
