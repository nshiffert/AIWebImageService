"""
Health check endpoints.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime

from ..db.database import get_db
from ..models.schemas import HealthResponse
from ..config import openai_client

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(db: Session = Depends(get_db)):
    """
    Health check endpoint.
    Checks database and OpenAI connectivity.
    """
    # Check database
    try:
        db.execute(text("SELECT 1"))
        db_status = "healthy"
    except Exception as e:
        db_status = f"unhealthy: {str(e)}"

    # Check OpenAI
    openai_status = "configured" if openai_client else "not configured"

    return HealthResponse(
        status="healthy" if db_status == "healthy" else "degraded",
        database=db_status,
        openai=openai_status,
        timestamp=datetime.now()
    )


@router.get("/ping")
async def ping():
    """Simple ping endpoint."""
    return {"ping": "pong", "timestamp": datetime.now().isoformat()}
