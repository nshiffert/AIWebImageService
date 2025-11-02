"""
Image generation service using OpenAI GPT Image models.
"""
import base64
import io
from typing import Dict, Tuple
from PIL import Image
from ..config import get_openai_client, settings


class ImageGenerator:
    """Handles image generation with OpenAI GPT Image models."""

    # Define size presets with dimensions
    SIZE_PRESETS = {
        'thumbnail': (150, 150),
        'product_card': (400, 300),
        'full_product': (800, 600),
        'hero_image': (1920, 600),
        'full_res': (2048, 2048)
    }

    def __init__(self):
        self.client = get_openai_client()
        self.model = "gpt-image-1"

    def _build_prompt(self, prompt: str, style: str = "product_photography") -> str:
        """
        Build an enhanced prompt based on style.

        Args:
            prompt: Base prompt from user
            style: Style preset to apply

        Returns:
            Enhanced prompt string
        """
        style_prefixes = {
            "product_photography": "Professional product photography, clean background, studio lighting, high quality: ",
            "lifestyle": "Lifestyle photography, natural lighting, authentic setting: ",
            "artistic": "Artistic food photography, creative composition: ",
            "rustic": "Rustic style, natural materials, warm tones: ",
        }

        prefix = style_prefixes.get(style, "High quality food photography: ")
        return prefix + prompt

    async def generate_image(
        self,
        prompt: str,
        style: str = "product_photography",
        size: str = "1024x1024",
        quality: str = "hd"
    ) -> Tuple[bytes, Dict]:
        """
        Generate a single image using OpenAI GPT Image model.

        Args:
            prompt: Image generation prompt
            style: Style preset (product_photography, lifestyle, artistic)
            size: Image size (1024x1024, 1024x1792, or 1792x1024)
            quality: Image quality ("standard" or "hd")

        Returns:
            Tuple of (image_bytes, generation_metadata)
        """
        enhanced_prompt = self._build_prompt(prompt, style)

        # Call OpenAI Image API
        # gpt-image-1 returns base64 data directly without response_format parameter
        response = await self.client.images.generate(
            model=self.model,
            prompt=enhanced_prompt
        )

        # gpt-image-1 returns base64 encoded image data by default
        if hasattr(response.data[0], 'b64_json') and response.data[0].b64_json:
            image_b64 = response.data[0].b64_json
            image_bytes = base64.b64decode(image_b64)
        else:
            raise ValueError(f"Unexpected response format from {self.model}")

        # Calculate cost (GPT Image pricing)
        cost = 0.04 if size == "1024x1024" else 0.08  # HD quality pricing

        metadata = {
            "model": self.model,
            "size": size,
            "quality": quality,
            "cost": cost,
            "revised_prompt": response.data[0].revised_prompt if hasattr(response.data[0], 'revised_prompt') else None
        }

        return image_bytes, metadata

    def create_variants(self, image_bytes: bytes) -> Dict[str, bytes]:
        """
        Create multiple size variants from a master image.

        Args:
            image_bytes: Original image bytes (typically full_res)

        Returns:
            Dict mapping size_preset to image bytes
        """
        img = Image.open(io.BytesIO(image_bytes))
        variants = {}

        for preset_name, (width, height) in self.SIZE_PRESETS.items():
            variant = self._resize_and_crop(img, width, height)

            # Convert to bytes
            buffer = io.BytesIO()
            variant.save(buffer, format='JPEG', quality=90, optimize=True)
            variants[preset_name] = buffer.getvalue()

        return variants

    def _resize_and_crop(self, img: Image.Image, target_width: int, target_height: int) -> Image.Image:
        """
        Resize and crop image to exact dimensions while maintaining aspect ratio.

        Args:
            img: PIL Image object
            target_width: Target width in pixels
            target_height: Target height in pixels

        Returns:
            Resized and cropped PIL Image
        """
        # Calculate aspect ratios
        img_ratio = img.width / img.height
        target_ratio = target_width / target_height

        if img_ratio > target_ratio:
            # Image is wider than target - crop width
            new_height = target_height
            new_width = int(new_height * img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Center crop
            left = (new_width - target_width) // 2
            img = img.crop((left, 0, left + target_width, target_height))
        else:
            # Image is taller than target - crop height
            new_width = target_width
            new_height = int(new_width / img_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)

            # Center crop
            top = (new_height - target_height) // 2
            img = img.crop((0, top, target_width, top + target_height))

        return img

    def extract_colors(self, image_bytes: bytes, num_colors: int = 5) -> list:
        """
        Extract dominant colors from an image.

        Args:
            image_bytes: Image file bytes
            num_colors: Number of colors to extract

        Returns:
            List of dicts with color_hex, percentage, and is_dominant
        """
        from colorthief import ColorThief

        color_thief = ColorThief(io.BytesIO(image_bytes))
        palette = color_thief.get_palette(color_count=num_colors, quality=1)

        colors = []
        for i, rgb in enumerate(palette):
            hex_color = '#{:02x}{:02x}{:02x}'.format(*rgb)
            colors.append({
                "color_hex": hex_color,
                "percentage": (num_colors - i) * (100 / sum(range(1, num_colors + 1))),
                "is_dominant": i == 0
            })

        return colors

    def get_cost_estimate(self, size: str = "1024x1024", quality: str = "hd") -> float:
        """
        Get cost estimate for image generation.

        Args:
            size: Image size
            quality: Image quality

        Returns:
            Estimated cost in USD
        """
        if quality == "hd":
            return 0.04 if size == "1024x1024" else 0.08
        else:  # standard quality
            return 0.02 if size == "1024x1024" else 0.04
