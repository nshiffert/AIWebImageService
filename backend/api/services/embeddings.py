"""
Embeddings service for creating vector representations of images.
Uses OpenAI's text-embedding-ada-002 model.
"""
from typing import List
from ..config import get_openai_client


class EmbeddingService:
    """Creates embeddings for semantic search."""

    def __init__(self):
        self.client = get_openai_client()
        self.model = "text-embedding-ada-002"
        self.embedding_dimensions = 1536

    async def create_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for a single text string.

        Args:
            text: Text to embed

        Returns:
            List of floats representing the embedding vector
        """
        response = await self.client.embeddings.create(
            model=self.model,
            input=text
        )

        return response.data[0].embedding

    async def create_image_embedding(
        self,
        prompt: str,
        tags: List[str],
        description: str,
        category: str = ""
    ) -> List[float]:
        """
        Create a rich embedding for image searchability.
        Combines prompt, tags, description, and category into a searchable vector.

        Args:
            prompt: Original generation prompt
            tags: List of image tags
            description: AI-generated description
            category: Image category (e.g., "cookies", "bread")

        Returns:
            List of floats representing the combined embedding
        """
        # Combine all text elements with appropriate weighting
        combined_parts = [
            f"Image: {prompt}",  # Original prompt is important
            f"Description: {description}",  # AI description provides context
        ]

        if category:
            combined_parts.append(f"Category: {category}")

        if tags:
            combined_parts.append(f"Tags: {', '.join(tags)}")

        combined_text = " ".join(combined_parts)

        return await self.create_embedding(combined_text)

    async def create_query_embedding(self, query: str) -> List[float]:
        """
        Create an embedding for a search query.
        Optimized for matching against image embeddings.

        Args:
            query: User search query

        Returns:
            List of floats representing the query embedding
        """
        # Add context to help with matching
        enhanced_query = f"Find an image of: {query}"

        return await self.create_embedding(enhanced_query)

    def get_model_info(self) -> dict:
        """Get information about the embedding model."""
        return {
            "model": self.model,
            "dimensions": self.embedding_dimensions,
            "provider": "openai"
        }
