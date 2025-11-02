"""
SQLAlchemy database models.
"""
from sqlalchemy import Column, String, Float, Integer, Boolean, Text, TIMESTAMP, ForeignKey, CheckConstraint, DECIMAL, JSON
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
import uuid
from .database import Base


class Image(Base):
    """Core image table."""
    __tablename__ = "images"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt = Column(Text, nullable=False)
    style = Column(String(50), default='product_photography')
    status = Column(String(20), default='pending')
    auto_tagged = Column(Boolean, default=False)
    tagging_confidence = Column(Float)
    generation_cost = Column(DECIMAL(10, 4))
    tagging_cost = Column(DECIMAL(10, 4))
    error_message = Column(Text)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    approved_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    variants = relationship("ImageVariant", back_populates="image", cascade="all, delete-orphan")
    tags = relationship("ImageTag", back_populates="image", cascade="all, delete-orphan")
    description = relationship("ImageDescription", back_populates="image", uselist=False, cascade="all, delete-orphan")
    colors = relationship("ImageColor", back_populates="image", cascade="all, delete-orphan")
    embedding = relationship("ImageEmbedding", back_populates="image", uselist=False, cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'processing', 'tagging', 'ready', 'approved', 'rejected'])),
    )


class ImageVariant(Base):
    """Image size variants."""
    __tablename__ = "image_variants"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='CASCADE'), nullable=False)
    size_preset = Column(String(20), nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    storage_path = Column(Text, nullable=False)
    file_size_bytes = Column(Integer)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="variants")

    __table_args__ = (
        CheckConstraint(size_preset.in_(['thumbnail', 'product_card', 'full_product', 'hero_image', 'full_res'])),
    )


class ImageTag(Base):
    """Image tags with source tracking."""
    __tablename__ = "image_tags"

    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='CASCADE'), primary_key=True)
    tag = Column(String(50), primary_key=True)
    confidence = Column(Float, default=1.0)
    source = Column(String(20), default='auto')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="tags")

    __table_args__ = (
        CheckConstraint(source.in_(['auto', 'manual', 'template'])),
    )


class ImageDescription(Base):
    """AI-generated image descriptions."""
    __tablename__ = "image_descriptions"

    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='CASCADE'), primary_key=True)
    description = Column(Text, nullable=False)
    vision_analysis = Column(JSON)
    model_version = Column(String(50))
    generated_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="description")


class ImageColor(Base):
    """Color analysis for images."""
    __tablename__ = "image_colors"

    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='CASCADE'), primary_key=True)
    color_hex = Column(String(7), primary_key=True)
    percentage = Column(Float, nullable=False)
    is_dominant = Column(Boolean, default=False)

    # Relationships
    image = relationship("Image", back_populates="colors")

    __table_args__ = (
        CheckConstraint('percentage >= 0 AND percentage <= 100'),
    )


class ImageEmbedding(Base):
    """Vector embeddings for semantic search."""
    __tablename__ = "image_embeddings"

    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='CASCADE'), primary_key=True)
    embedding = Column(Vector(1536), nullable=False)  # OpenAI text-embedding-ada-002 dimension
    embedding_source = Column(Text)
    model_version = Column(String(50), default='text-embedding-ada-002')
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())

    # Relationships
    image = relationship("Image", back_populates="embedding")


class GenerationJob(Base):
    """Tracks batch image generation jobs."""
    __tablename__ = "generation_jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    status = Column(String(20), default='pending', nullable=False)
    total_tasks = Column(Integer, default=0, nullable=False)
    completed_tasks = Column(Integer, default=0, nullable=False)
    failed_tasks = Column(Integer, default=0, nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    completed_at = Column(TIMESTAMP(timezone=True))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    tasks = relationship("GenerationTask", back_populates="job", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'running', 'completed', 'failed', 'cancelled'])),
    )


class GenerationTask(Base):
    """Individual image generation tasks within a batch job."""
    __tablename__ = "generation_tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id = Column(UUID(as_uuid=True), ForeignKey('generation_jobs.id', ondelete='CASCADE'), nullable=False)
    prompt = Column(Text, nullable=False)
    style = Column(String(50), default='product_photography')
    status = Column(String(20), default='pending', nullable=False)
    image_id = Column(UUID(as_uuid=True), ForeignKey('images.id', ondelete='SET NULL'))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at = Column(TIMESTAMP(timezone=True))
    completed_at = Column(TIMESTAMP(timezone=True))

    # Relationships
    job = relationship("GenerationJob", back_populates="tasks")
    image = relationship("Image")

    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'running', 'completed', 'failed'])),
    )


class APIKey(Base):
    """API keys for search endpoint authentication."""
    __tablename__ = "api_keys"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100))
    key_hash = Column(Text, unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    rate_limit = Column(Integer, default=100)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
    last_used_at = Column(TIMESTAMP(timezone=True))


class SearchCache(Base):
    """Cache for search results."""
    __tablename__ = "search_cache"

    cache_key = Column(String(32), primary_key=True)
    query = Column(Text, nullable=False)
    size = Column(String(20))
    results = Column(JSON, nullable=False)
    expires_at = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at = Column(TIMESTAMP(timezone=True), server_default=func.now())
