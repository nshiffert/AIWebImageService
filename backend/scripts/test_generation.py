"""
Simple test script to generate a test image.
Run this after the Docker services are up to verify everything works.
"""
import asyncio
import sys
sys.path.append('/app')

from sqlalchemy.orm import Session
from api.db.database import SessionLocal
from api.routers.admin import process_single_image


async def test_generate():
    """Generate a test image."""
    db = SessionLocal()

    try:
        print("=" * 60)
        print("Testing Image Generation")
        print("=" * 60)

        prompt = "chocolate chip cookies on a white plate"
        style = "product_photography"

        print(f"\nPrompt: {prompt}")
        print(f"Style: {style}\n")

        image_id = await process_single_image(prompt, style, db)

        print(f"\n{'=' * 60}")
        print(f"SUCCESS! Image ID: {image_id}")
        print(f"{'=' * 60}")
        print("\nYou can now:")
        print("1. Check http://localhost:8000/api/admin/images/review to see the image")
        print("2. Approve it via POST http://localhost:8000/api/admin/images/{image_id}/approve")
        print("3. Search for it via POST http://localhost:8000/api/v1/search")
        print("\n")

    except Exception as e:
        print(f"\n{'=' * 60}")
        print(f"ERROR: {str(e)}")
        print(f"{'=' * 60}")
        import traceback
        traceback.print_exc()
    finally:
        db.close()


if __name__ == "__main__":
    asyncio.run(test_generate())
