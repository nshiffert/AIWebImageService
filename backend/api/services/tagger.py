"""
Auto-tagging service using GPT-4 Vision.
Analyzes images and generates searchable tags.
"""
import base64
import json
from typing import Dict, List
from ..config import get_openai_client, settings


class AutoTagger:
    """Analyzes images and generates tags using GPT-4 Vision."""

    def __init__(self):
        self.client = get_openai_client()
        self.vision_model = "gpt-4o"  # GPT-4o has vision capabilities
        self.text_model = "gpt-4o"  # Using same model for consistency

    async def analyze_and_tag(
        self,
        image_bytes: bytes,
        original_prompt: str
    ) -> Dict:
        """
        Analyze an image with GPT-4 Vision and generate tags.

        Args:
            image_bytes: Image file bytes
            original_prompt: The original generation prompt

        Returns:
            Dict with tags, category, description, and analysis data
        """
        # Encode image to base64
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        # First, use GPT-4 Vision to analyze the image
        vision_response = await self.client.chat.completions.create(
            model=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": """Analyze this cottage food product image and provide a detailed JSON response with:
1. main_items: List of main food items visible
2. presentation_style: How the food is presented
3. props_surfaces: Any props, plates, surfaces visible
4. visual_style: The overall visual style and mood
5. colors: Dominant color characteristics
6. setting: The setting or context of the image

Return ONLY valid JSON, no other text."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }],
            max_tokens=500
        )

        vision_content = vision_response.choices[0].message.content

        # Parse vision analysis
        try:
            vision_analysis = json.loads(vision_content)
        except json.JSONDecodeError:
            # If JSON parsing fails, create a basic structure
            vision_analysis = {
                "main_items": ["food"],
                "presentation_style": "unknown",
                "raw_response": vision_content
            }

        # Now use GPT-4 to generate specific searchable tags
        tags_response = await self.client.chat.completions.create(
            model=self.text_model,
            messages=[
                {
                    "role": "system",
                    "content": """You are an expert at generating search tags for cottage food product images.
Generate 8-12 specific, searchable tags that small food businesses would use to find this image.
Include: food type, preparation method, presentation style, colors, setting.
Tags should be lowercase, hyphenated when needed (e.g., "chocolate-chip", "wooden-board").
Return valid JSON with: tags (array), category (string), description (string)."""
                },
                {
                    "role": "user",
                    "content": f"""Original prompt: {original_prompt}

Vision analysis: {json.dumps(vision_analysis)}

Generate searchable tags for this cottage food image."""
                }
            ],
            response_format={"type": "json_object"}
        )

        tags_content = tags_response.choices[0].message.content
        tags_data = json.loads(tags_content)

        # Ensure tags are in the right format
        tags = tags_data.get("tags", [])
        if isinstance(tags, str):
            tags = [t.strip() for t in tags.split(",")]

        # Limit to max tags
        tags = tags[:settings.max_tags_per_image]

        # Calculate confidence score based on response quality
        confidence = self._calculate_confidence(vision_analysis, tags)

        return {
            "tags": tags,
            "category": tags_data.get("category", "food"),
            "description": tags_data.get("description", ""),
            "vision_analysis": vision_analysis,
            "confidence": confidence,
            "model_version": self.vision_model
        }

    async def generate_description(
        self,
        image_bytes: bytes,
        tags: List[str],
        category: str
    ) -> str:
        """
        Generate a natural language description of the image.

        Args:
            image_bytes: Image file bytes
            tags: List of tags for the image
            category: Image category

        Returns:
            Description string
        """
        # Encode image
        image_b64 = base64.b64encode(image_bytes).decode('utf-8')

        response = await self.client.chat.completions.create(
            model=self.vision_model,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": f"""Write a concise, appealing description of this {category} image.
The description should be 1-2 sentences and include these elements: {', '.join(tags[:5])}.
Make it natural and appealing for a cottage food business website."""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }],
            max_tokens=150
        )

        return response.choices[0].message.content.strip()

    def _calculate_confidence(
        self,
        vision_analysis: Dict,
        tags: List[str]
    ) -> float:
        """
        Calculate confidence score for the tagging.

        Args:
            vision_analysis: Vision analysis data
            tags: Generated tags

        Returns:
            Confidence score between 0 and 1
        """
        score = 0.5  # Base score

        # More tags = higher confidence (up to a point)
        if len(tags) >= 8:
            score += 0.2

        # Having main_items identified = higher confidence
        if vision_analysis.get("main_items") and len(vision_analysis["main_items"]) > 0:
            score += 0.15

        # Having detailed analysis = higher confidence
        if len(vision_analysis.keys()) >= 4:
            score += 0.15

        return min(score, 1.0)

    async def get_tagging_cost_estimate(self) -> float:
        """
        Estimate the cost of tagging one image.

        Returns:
            Estimated cost in USD
        """
        # GPT-4 Vision: ~$0.01 per image (rough estimate)
        # GPT-4 Turbo for tags: ~$0.002
        return 0.012
