"""
Queue service for enqueueing image generation tasks.
Supports both local development (HTTP) and production (Cloud Tasks).
"""
import os
import logging
from typing import Optional
from uuid import UUID
import httpx

logger = logging.getLogger(__name__)


class QueueService:
    """Handles enqueueing generation tasks."""

    def __init__(self):
        self.environment = os.getenv("ENVIRONMENT", "local")
        self.worker_url = os.getenv("WORKER_URL", "http://localhost:8000/api/admin/worker/process-task")
        self.use_cloud_tasks = os.getenv("USE_CLOUD_TASKS", "false").lower() == "true"

        # Cloud Tasks configuration (for production)
        self.gcp_project = os.getenv("GCP_PROJECT")
        self.gcp_location = os.getenv("GCP_LOCATION", "us-central1")
        self.queue_name = os.getenv("QUEUE_NAME", "image-generation")

    async def enqueue_task(self, task_id: UUID) -> bool:
        """
        Enqueue a generation task for processing.

        Args:
            task_id: UUID of the task to process

        Returns:
            True if successfully enqueued, False otherwise
        """
        if self.use_cloud_tasks and self.environment == "production":
            return await self._enqueue_cloud_task(task_id)
        else:
            return await self._enqueue_local_task(task_id)

    async def _enqueue_local_task(self, task_id: UUID) -> bool:
        """
        Enqueue task locally using direct HTTP call.
        This simulates Cloud Tasks behavior for local development.

        Args:
            task_id: UUID of the task to process

        Returns:
            True if successfully enqueued
        """
        try:
            # Make async HTTP request to worker endpoint
            async with httpx.AsyncClient(timeout=300.0) as client:
                response = await client.post(
                    self.worker_url,
                    json={"task_id": str(task_id)}
                )

                if response.status_code == 200:
                    logger.info(f"Task {task_id} enqueued locally")
                    return True
                else:
                    logger.error(f"Failed to enqueue task {task_id}: {response.status_code}")
                    return False

        except Exception as e:
            logger.error(f"Error enqueueing local task {task_id}: {e}")
            return False

    async def _enqueue_cloud_task(self, task_id: UUID) -> bool:
        """
        Enqueue task using GCP Cloud Tasks.

        Args:
            task_id: UUID of the task to process

        Returns:
            True if successfully enqueued
        """
        try:
            from google.cloud import tasks_v2
            from google.protobuf import timestamp_pb2
            import datetime
            import json

            # Create Cloud Tasks client
            client = tasks_v2.CloudTasksClient()

            # Construct the fully qualified queue name
            parent = client.queue_path(self.gcp_project, self.gcp_location, self.queue_name)

            # Construct the task
            task = {
                "http_request": {
                    "http_method": tasks_v2.HttpMethod.POST,
                    "url": self.worker_url,
                    "headers": {"Content-Type": "application/json"},
                    "body": json.dumps({"task_id": str(task_id)}).encode(),
                }
            }

            # Add authentication for Cloud Run
            if "run.app" in self.worker_url:
                task["http_request"]["oidc_token"] = {
                    "service_account_email": os.getenv("CLOUD_TASKS_SERVICE_ACCOUNT")
                }

            # Create the task
            response = client.create_task(request={"parent": parent, "task": task})

            logger.info(f"Cloud Task created for task {task_id}: {response.name}")
            return True

        except Exception as e:
            logger.error(f"Error creating Cloud Task for {task_id}: {e}")
            return False

    async def enqueue_batch(self, task_ids: list[UUID]) -> dict:
        """
        Enqueue multiple tasks with controlled concurrency for local development.

        Args:
            task_ids: List of task UUIDs to enqueue

        Returns:
            Dict with success/failure counts
        """
        import asyncio

        # Controlled concurrency for local development (max 5 concurrent tasks)
        max_concurrent = int(os.getenv("MAX_CONCURRENT_LOCAL_TASKS", "5"))
        semaphore = asyncio.Semaphore(max_concurrent)

        async def enqueue_with_limit(task_id: UUID) -> bool:
            """Enqueue a single task with semaphore control."""
            async with semaphore:
                return await self.enqueue_task(task_id)

        # Process all tasks with controlled concurrency
        enqueue_tasks = [enqueue_with_limit(task_id) for task_id in task_ids]
        results_list = await asyncio.gather(*enqueue_tasks, return_exceptions=True)

        # Count successes and failures
        results = {"enqueued": 0, "failed": 0}
        for result in results_list:
            if isinstance(result, Exception):
                results["failed"] += 1
                logger.error(f"Task enqueue failed with exception: {result}")
            elif result is True:
                results["enqueued"] += 1
            else:
                results["failed"] += 1

        return results


# Singleton instance
_queue_service: Optional[QueueService] = None


def get_queue_service() -> QueueService:
    """Get or create the queue service instance."""
    global _queue_service
    if _queue_service is None:
        _queue_service = QueueService()
    return _queue_service
