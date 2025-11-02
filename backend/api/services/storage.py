"""
Storage service for managing image files locally.
For local development, stores files in the filesystem.
"""
import os
from pathlib import Path
from typing import Dict
from uuid import UUID
from ..config import settings


class StorageService:
    """Handles local file storage for images."""

    def __init__(self):
        self.storage_path = Path(settings.storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)

    def get_image_directory(self, image_id: UUID) -> Path:
        """Get the directory path for an image's variants."""
        img_dir = self.storage_path / str(image_id)
        img_dir.mkdir(parents=True, exist_ok=True)
        return img_dir

    async def save_image(
        self,
        image_bytes: bytes,
        image_id: UUID,
        size_preset: str
    ) -> Dict[str, str]:
        """
        Save an image to local storage.

        Args:
            image_bytes: The image file bytes
            image_id: UUID of the image
            size_preset: Size preset name (thumbnail, product_card, etc.)

        Returns:
            Dict with storage_path and file_size
        """
        img_dir = self.get_image_directory(image_id)
        file_path = img_dir / f"{size_preset}.jpg"

        # Write image to disk
        with open(file_path, 'wb') as f:
            f.write(image_bytes)

        # Get relative path from storage root
        relative_path = str(file_path.relative_to(self.storage_path))

        return {
            "storage_path": relative_path,
            "file_size_bytes": len(image_bytes)
        }

    async def get_image(self, storage_path: str) -> bytes:
        """
        Retrieve an image from local storage.

        Args:
            storage_path: Relative path to the image file

        Returns:
            Image file bytes
        """
        file_path = self.storage_path / storage_path

        if not file_path.exists():
            raise FileNotFoundError(f"Image not found: {storage_path}")

        with open(file_path, 'rb') as f:
            return f.read()

    async def delete_image(self, image_id: UUID) -> None:
        """
        Delete all variants of an image.

        Args:
            image_id: UUID of the image to delete
        """
        img_dir = self.get_image_directory(image_id)

        if img_dir.exists():
            # Delete all files in the directory
            for file_path in img_dir.iterdir():
                file_path.unlink()
            # Remove the directory
            img_dir.rmdir()

    def get_storage_stats(self) -> Dict[str, float]:
        """
        Get storage statistics.

        Returns:
            Dict with storage usage information
        """
        total_size = 0
        file_count = 0

        for root, dirs, files in os.walk(self.storage_path):
            for file in files:
                file_path = Path(root) / file
                total_size += file_path.stat().st_size
                file_count += 1

        return {
            "total_size_mb": total_size / (1024 * 1024),
            "file_count": file_count
        }

    def get_public_url(self, storage_path: str) -> str:
        """
        Get a public URL for an image.
        For local development, returns a relative path.
        In production, this would return a CDN URL.

        Args:
            storage_path: Relative path to the image file

        Returns:
            Public URL or path to the image
        """
        # For local development
        return f"/storage/{storage_path}"
