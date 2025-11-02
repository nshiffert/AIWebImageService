"""
Service layer for managing generation jobs and tasks.
"""
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from ..db.models import GenerationJob, GenerationTask
from ..models.schemas import JobStatusResponse


class JobService:
    """Handles creation and management of generation jobs."""

    @staticmethod
    def create_job(db: Session, prompts: List[str], style: str = "product_photography", count_per_prompt: int = 1) -> GenerationJob:
        """
        Create a new generation job with tasks.

        Args:
            db: Database session
            prompts: List of prompts to generate images for
            style: Image style
            count_per_prompt: Number of images per prompt

        Returns:
            Created GenerationJob instance
        """
        # Calculate total tasks
        total_tasks = len(prompts) * count_per_prompt

        # Create job
        job = GenerationJob(
            status='pending',
            total_tasks=total_tasks,
            completed_tasks=0,
            failed_tasks=0
        )
        db.add(job)
        db.flush()  # Get job.id

        # Create tasks
        tasks = []
        for prompt in prompts:
            for _ in range(count_per_prompt):
                task = GenerationTask(
                    job_id=job.id,
                    prompt=prompt,
                    style=style,
                    status='pending'
                )
                tasks.append(task)

        db.add_all(tasks)
        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def get_job(db: Session, job_id: UUID) -> Optional[GenerationJob]:
        """Get a job by ID with all tasks."""
        return db.query(GenerationJob).filter(GenerationJob.id == job_id).first()

    @staticmethod
    def get_job_status(db: Session, job_id: UUID) -> Optional[JobStatusResponse]:
        """
        Get lightweight job status for polling.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            JobStatusResponse or None if not found
        """
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()

        if not job:
            return None

        # Calculate progress percentage
        progress = 0.0
        if job.total_tasks > 0:
            progress = (job.completed_tasks + job.failed_tasks) / job.total_tasks * 100

        return JobStatusResponse(
            id=job.id,
            status=job.status,
            total_tasks=job.total_tasks,
            completed_tasks=job.completed_tasks,
            failed_tasks=job.failed_tasks,
            progress_percentage=round(progress, 2),
            created_at=job.created_at,
            completed_at=job.completed_at
        )

    @staticmethod
    def get_pending_task(db: Session, job_id: UUID) -> Optional[GenerationTask]:
        """Get the next pending task for a job."""
        return db.query(GenerationTask).filter(
            GenerationTask.job_id == job_id,
            GenerationTask.status == 'pending'
        ).first()

    @staticmethod
    def get_task(db: Session, task_id: UUID) -> Optional[GenerationTask]:
        """Get a task by ID."""
        return db.query(GenerationTask).filter(GenerationTask.id == task_id).first()

    @staticmethod
    def update_task_status(
        db: Session,
        task_id: UUID,
        status: str,
        image_id: Optional[UUID] = None,
        error_message: Optional[str] = None
    ) -> Optional[GenerationTask]:
        """
        Update task status and related fields.

        Args:
            db: Database session
            task_id: Task UUID
            status: New status ('running', 'completed', 'failed')
            image_id: Generated image ID (for completed tasks)
            error_message: Error message (for failed tasks)

        Returns:
            Updated task or None
        """
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()

        if not task:
            return None

        task.status = status

        if status == 'running':
            task.started_at = datetime.utcnow()
        elif status in ['completed', 'failed']:
            task.completed_at = datetime.utcnow()

            if status == 'completed' and image_id:
                task.image_id = image_id
            elif status == 'failed' and error_message:
                task.error_message = error_message
                task.retry_count += 1

        db.commit()
        db.refresh(task)

        # Update job status
        JobService.update_job_progress(db, task.job_id)

        return task

    @staticmethod
    def update_job_progress(db: Session, job_id: UUID) -> Optional[GenerationJob]:
        """
        Update job progress based on task statuses.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            Updated job or None
        """
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()

        if not job:
            return None

        # Count completed and failed tasks
        completed = db.query(func.count(GenerationTask.id)).filter(
            GenerationTask.job_id == job_id,
            GenerationTask.status == 'completed'
        ).scalar()

        failed = db.query(func.count(GenerationTask.id)).filter(
            GenerationTask.job_id == job_id,
            GenerationTask.status == 'failed'
        ).scalar()

        job.completed_tasks = completed
        job.failed_tasks = failed

        # Update job status
        if completed + failed >= job.total_tasks:
            # All tasks done
            if failed >= job.total_tasks:
                job.status = 'failed'
            else:
                job.status = 'completed'
            job.completed_at = datetime.utcnow()
        elif completed + failed > 0:
            job.status = 'running'

        db.commit()
        db.refresh(job)

        return job

    @staticmethod
    def mark_task_for_retry(db: Session, task_id: UUID) -> Optional[GenerationTask]:
        """
        Mark a failed task for retry.

        Args:
            db: Database session
            task_id: Task UUID

        Returns:
            Updated task or None
        """
        task = db.query(GenerationTask).filter(GenerationTask.id == task_id).first()

        if not task or task.retry_count >= 3:
            return None

        task.status = 'pending'
        task.error_message = None
        task.started_at = None
        task.completed_at = None

        db.commit()
        db.refresh(task)

        return task

    @staticmethod
    def cancel_job(db: Session, job_id: UUID) -> Optional[GenerationJob]:
        """
        Cancel a job and all pending tasks.

        Args:
            db: Database session
            job_id: Job UUID

        Returns:
            Updated job or None
        """
        job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()

        if not job:
            return None

        # Update job status
        job.status = 'cancelled'
        job.completed_at = datetime.utcnow()

        # Cancel all pending tasks
        db.query(GenerationTask).filter(
            GenerationTask.job_id == job_id,
            GenerationTask.status == 'pending'
        ).update({'status': 'failed', 'error_message': 'Job cancelled'})

        db.commit()
        db.refresh(job)

        return job
