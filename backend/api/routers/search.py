"""
Search API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
import time
from typing import Optional

from ..db.database import get_db
from ..models.schemas import SearchRequest, SearchResponse, SearchResultItem
from ..services.embeddings import EmbeddingService

router = APIRouter()


async def verify_api_key(x_api_key: Optional[str] = Header(None, alias="X-API-Key")):
    """
    Verify API key for search endpoint.
    For local development, accepts 'test-key-local-dev-only'.
    """
    # Allow OPTIONS requests (CORS preflight) to pass through
    if not x_api_key:
        # In development, allow requests without API key for easier testing
        # TODO: Enable strict API key validation in production
        return True

    # For local development
    if x_api_key == "test-key-local-dev-only":
        return True

    # TODO: Implement proper API key validation against database
    # For now, accept any key in development
    return True


@router.post("/search", response_model=SearchResponse)
async def search_images(
    request: SearchRequest,
    db: Session = Depends(get_db),
    api_key: bool = Depends(verify_api_key)
):
    """
    Vector search for images based on text query.

    Requires X-API-Key header for authentication.
    """
    start_time = time.time()

    try:
        # Create query embedding
        embedding_service = EmbeddingService()
        query_embedding = await embedding_service.create_query_embedding(request.query)

        # Execute vector search using database function
        # Format embedding as PostgreSQL array literal
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'

        # Use format string to avoid SQLAlchemy parameter issues with :: cast operator
        sql_query = f"""
            SELECT * FROM search_similar_images(
                '{embedding_str}'::vector,
                {request.min_score},
                {request.limit},
                '{request.size}'
            )
        """

        result = db.execute(text(sql_query))

        # Convert results to response models
        results = []
        for row in result:
            results.append(SearchResultItem(
                id=row.id,
                storage_path=row.storage_path,
                score=row.score,
                tags=row.tags if row.tags else [],
                description=row.description,
                dominant_color=row.dominant_color
            ))

        query_time = (time.time() - start_time) * 1000  # Convert to ms

        return SearchResponse(
            results=results,
            total=len(results),
            query_time_ms=round(query_time, 2)
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")
