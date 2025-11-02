"""
Admin API endpoints for image management.
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text, func
from uuid import UUID
import asyncio
from datetime import datetime

from ..db.database import get_db
from ..db.models import Image, ImageVariant, ImageTag, ImageDescription, ImageColor, ImageEmbedding, GenerationJob, GenerationTask
from ..models.schemas import (
    GenerateImageRequest,
    GenerateBatchRequest,
    ApproveImageRequest,
    GenerationStatusResponse,
    ImageResponse,
    StatsResponse,
    GenerationJobResponse,
    JobStatusResponse
)
from ..services.generator import ImageGenerator
from ..services.tagger import AutoTagger
from ..services.embeddings import EmbeddingService
from ..services.storage import StorageService
from ..services.job_service import JobService
from ..services.queue_service import get_queue_service

router = APIRouter()


async def process_single_image(
    prompt: str,
    style: str,
    db: Session
) -> UUID:
    """
    Process a single image: generate, create variants, tag, and store.

    Args:
        prompt: Image generation prompt
        style: Image style
        db: Database session

    Returns:
        UUID of created image
    """
    generator = ImageGenerator()
    tagger = AutoTagger()
    embedding_service = EmbeddingService()
    storage = StorageService()

    # Create image record
    image = Image(
        prompt=prompt,
        style=style,
        status='processing'
    )
    db.add(image)
    db.commit()
    db.refresh(image)

    try:
        # Generate image
        print(f"Generating image for: {prompt[:50]}...")
        master_bytes, metadata = await generator.generate_image(prompt, style)

        image.generation_cost = metadata['cost']
        image.status = 'tagging'
        db.commit()

        # Create size variants
        print(f"Creating size variants...")
        variants = generator.create_variants(master_bytes)

        # Store all variants
        for size_preset, variant_bytes in variants.items():
            storage_info = await storage.save_image(
                variant_bytes,
                image.id,
                size_preset
            )

            # Get dimensions
            width, height = generator.SIZE_PRESETS[size_preset]

            variant = ImageVariant(
                image_id=image.id,
                size_preset=size_preset,
                width=width,
                height=height,
                storage_path=storage_info['storage_path'],
                file_size_bytes=storage_info['file_size_bytes']
            )
            db.add(variant)

        db.commit()

        # Auto-tag with GPT-4 Vision
        print(f"Auto-tagging with GPT-4 Vision...")
        tagging_result = await tagger.analyze_and_tag(master_bytes, prompt)

        image.auto_tagged = True
        image.tagging_confidence = tagging_result['confidence']
        image.tagging_cost = await tagger.get_tagging_cost_estimate()

        # Save tags
        for tag_text in tagging_result['tags']:
            tag = ImageTag(
                image_id=image.id,
                tag=tag_text,
                confidence=tagging_result['confidence'],
                source='auto'
            )
            db.add(tag)

        # Save description
        description = ImageDescription(
            image_id=image.id,
            description=tagging_result['description'],
            vision_analysis=tagging_result['vision_analysis'],
            model_version=tagging_result['model_version']
        )
        db.add(description)

        # Extract and save colors
        colors = generator.extract_colors(master_bytes)
        for color_data in colors:
            color = ImageColor(
                image_id=image.id,
                color_hex=color_data['color_hex'],
                percentage=color_data['percentage'],
                is_dominant=color_data['is_dominant']
            )
            db.add(color)

        db.commit()

        # Create embedding for search
        print(f"Creating search embedding...")
        embedding_vector = await embedding_service.create_image_embedding(
            prompt=prompt,
            tags=tagging_result['tags'],
            description=tagging_result['description'],
            category=tagging_result['category']
        )

        embedding = ImageEmbedding(
            image_id=image.id,
            embedding=embedding_vector,
            embedding_source=f"prompt+tags+description",
            model_version='text-embedding-ada-002'
        )
        db.add(embedding)

        # Mark as ready for review
        image.status = 'ready'
        db.commit()

        print(f"✓ Image {image.id} completed successfully")
        return image.id

    except Exception as e:
        print(f"✗ Error processing image: {str(e)}")
        image.status = 'rejected'
        image.error_message = str(e)
        db.commit()
        raise


@router.post("/generate", response_model=GenerationStatusResponse)
async def generate_single_image(
    request: GenerateImageRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Generate a single image.
    This is an async operation that runs in the background.
    """
    try:
        image_id = await process_single_image(request.prompt, request.style, db)
        return GenerationStatusResponse(
            image_id=image_id,
            status="completed",
            message="Image generated and ready for review"
        )
    except Exception as e:
        return GenerationStatusResponse(
            status="failed",
            error=str(e)
        )


@router.post("/generate/batch", response_model=GenerationJobResponse)
async def generate_batch(
    request: GenerateBatchRequest,
    db: Session = Depends(get_db)
):
    """
    Generate multiple images from a list of prompts.
    Returns immediately with a job ID for tracking progress.
    """
    # Create job and tasks
    job = JobService.create_job(
        db=db,
        prompts=request.prompts,
        style=request.style,
        count_per_prompt=request.count_per_prompt
    )

    # Enqueue all tasks for processing
    queue_service = get_queue_service()
    task_ids = [task.id for task in job.tasks]

    # Enqueue tasks asynchronously
    enqueue_results = await queue_service.enqueue_batch(task_ids)

    print(f"Job {job.id} created with {len(task_ids)} tasks")
    print(f"Enqueued: {enqueue_results['enqueued']}, Failed: {enqueue_results['failed']}")

    return GenerationJobResponse.from_orm(job)


@router.post("/worker/process-task")
async def process_task(
    request: dict,
    db: Session = Depends(get_db)
):
    """
    Worker endpoint to process a single generation task.
    Called by queue service (local HTTP or Cloud Tasks).
    """
    # Extract task_id from request body
    task_id_str = request.get('task_id')
    if not task_id_str:
        raise HTTPException(status_code=400, detail="task_id is required")

    try:
        task_id = UUID(task_id_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid task_id format")

    # Get the task
    task = JobService.get_task(db, task_id)

    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != 'pending':
        return {"message": "Task already processed", "status": task.status}

    # Mark task as running
    JobService.update_task_status(db, task_id, 'running')

    try:
        # Process the image
        image_id = await process_single_image(task.prompt, task.style, db)

        # Mark task as completed
        JobService.update_task_status(db, task_id, 'completed', image_id=image_id)

        return {
            "task_id": str(task_id),
            "status": "completed",
            "image_id": str(image_id)
        }

    except Exception as e:
        # Mark task as failed
        error_msg = str(e)
        JobService.update_task_status(db, task_id, 'failed', error_message=error_msg)

        # Optionally retry if not exceeded retry limit
        if task.retry_count < 3:
            JobService.mark_task_for_retry(db, task_id)
            print(f"Task {task_id} marked for retry ({task.retry_count + 1}/3)")

        return {
            "task_id": str(task_id),
            "status": "failed",
            "error": error_msg
        }


@router.get("/jobs/{job_id}/status", response_model=JobStatusResponse)
async def get_job_status(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get the current status of a generation job.
    Used for polling progress.
    """
    status = JobService.get_job_status(db, job_id)

    if not status:
        raise HTTPException(status_code=404, detail="Job not found")

    return status


@router.get("/jobs/{job_id}", response_model=GenerationJobResponse)
async def get_job_details(
    job_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Get full details of a generation job including all tasks.
    """
    job = JobService.get_job(db, job_id)

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return GenerationJobResponse.from_orm(job)


@router.get("/images/review")
async def list_review_queue(
    limit: int = 20,
    db: Session = Depends(get_db)
):
    """
    List images pending review.
    """
    images = db.query(Image).filter(Image.status == 'ready').order_by(Image.created_at.desc()).limit(limit).all()

    # Convert to response format
    image_list = []
    for img in images:
        image_list.append({
            "id": str(img.id),
            "prompt": img.prompt,
            "style": img.style,
            "status": img.status,
            "description": img.description.description if img.description else None,
            "tags": [{"tag": t.tag, "confidence": t.confidence, "source": t.source} for t in img.tags],
            "created_at": img.created_at.isoformat(),
            "tagging_confidence": img.tagging_confidence
        })

    return {
        "images": image_list,
        "total": len(images)
    }


@router.post("/images/{image_id}/approve")
async def approve_image(
    image_id: UUID,
    request: ApproveImageRequest = ApproveImageRequest(),
    db: Session = Depends(get_db)
):
    """
    Approve an image for search index.
    Optionally override tags.
    """
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Override tags if provided
    if request.override_tags:
        # Delete existing tags
        db.query(ImageTag).filter(ImageTag.image_id == image_id).delete()

        # Add new tags
        for tag_text in request.override_tags:
            tag = ImageTag(
                image_id=image_id,
                tag=tag_text,
                confidence=1.0,
                source='manual'
            )
            db.add(tag)

    # Approve image
    image.status = 'approved'
    image.approved_at = datetime.now()
    db.commit()

    return {"message": "Image approved", "image_id": str(image_id)}


@router.delete("/images/{image_id}")
async def delete_image(
    image_id: UUID,
    db: Session = Depends(get_db)
):
    """Delete an image and all its data."""
    image = db.query(Image).filter(Image.id == image_id).first()

    if not image:
        raise HTTPException(status_code=404, detail="Image not found")

    # Delete from storage
    storage = StorageService()
    try:
        await storage.delete_image(image_id)
    except Exception as e:
        print(f"Warning: Could not delete files from storage: {e}")

    # Delete from database (cascades to related tables)
    db.delete(image)
    db.commit()

    return {"message": "Image deleted", "image_id": str(image_id)}


@router.get("/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get system statistics."""
    total_images = db.query(func.count(Image.id)).scalar()
    approved_images = db.query(func.count(Image.id)).filter(Image.status == 'approved').scalar()
    pending_review = db.query(func.count(Image.id)).filter(Image.status == 'ready').scalar()
    total_tags = db.query(func.count(ImageTag.tag.distinct())).scalar()

    # Storage stats
    storage = StorageService()
    storage_stats = storage.get_storage_stats()

    return StatsResponse(
        total_images=total_images or 0,
        approved_images=approved_images or 0,
        pending_review=pending_review or 0,
        total_tags=total_tags or 0,
        storage_used_mb=storage_stats['total_size_mb']
    )
