"""Image processing service for TheFrame application."""

import asyncio
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import aiohttp
import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..core.exceptions import ImageProcessingError
from ..core.models import Artwork, ArtworkMetadata


class ImageProcessor:
    """Service for processing artwork images."""
    
    def __init__(self, font_path: Optional[str] = None):
        self.font_path = font_path
        self.logger = logging.getLogger(__name__)
    
    async def download_image(self, url: str) -> bytes:
        """Download image from URL asynchronously."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.read()
                    else:
                        raise ImageProcessingError(
                            f"Failed to download image from {url}",
                            f"HTTP {response.status}"
                        )
        except Exception as e:
            raise ImageProcessingError(f"Failed to download image: {e}")
    
    def embed_metadata(self, image_data: bytes, artwork: Artwork) -> bytes:
        """Embed metadata into image as a overlay."""
        try:
            # Load the image
            image = Image.open(io.BytesIO(image_data))
            
            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')
            
            # Create a semi-transparent overlay
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)
            
            # Load font (use default if custom font fails)
            font_size = max(20, min(image.width, image.height) // 40)
            try:
                if self.font_path and Path(self.font_path).exists():
                    font = ImageFont.truetype(self.font_path, font_size)
                else:
                    font = ImageFont.load_default()
            except OSError:
                font = ImageFont.load_default()
            
            # Prepare metadata text
            metadata_text = self._format_metadata_text(artwork.metadata)
            
            # Calculate text dimensions and position
            text_bbox = draw.textbbox((0, 0), metadata_text, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # Position at bottom-left with padding
            padding = 20
            x = padding
            y = image.height - text_height - padding
            
            # Draw semi-transparent background
            bg_bbox = (x - 10, y - 10, x + text_width + 10, y + text_height + 10)
            draw.rectangle(bg_bbox, fill=(0, 0, 0, 180))
            
            # Draw text
            draw.text((x, y), metadata_text, font=font, fill=(255, 255, 255, 255))
            
            # Composite the overlay onto the original image
            image_with_overlay = Image.alpha_composite(
                image.convert('RGBA'), overlay
            ).convert('RGB')
            
            # Save to bytes
            output = io.BytesIO()
            image_with_overlay.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to embed metadata: {e}")
    
    def _format_metadata_text(self, metadata: ArtworkMetadata) -> str:
        """Format metadata for display on image."""
        lines = [
            f"'{metadata.title}'",
            f"by {metadata.author}",
        ]
        
        if metadata.year:
            lines.append(f"({metadata.year})")
        
        if metadata.style:
            lines.append(f"Style: {metadata.style}")
        
        return "\n".join(lines)
    
    def resize_image(self, image_data: bytes, max_width: int = 1920, max_height: int = 1080) -> bytes:
        """Resize image while maintaining aspect ratio."""
        try:
            image = Image.open(io.BytesIO(image_data))
            
            # Calculate new dimensions
            image.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Save to bytes
            output = io.BytesIO()
            image.save(output, format='JPEG', quality=95)
            return output.getvalue()
            
        except Exception as e:
            raise ImageProcessingError(f"Failed to resize image: {e}")
    
    def validate_image(self, image_data: bytes) -> Tuple[int, int]:
        """Validate image and return dimensions."""
        try:
            image = Image.open(io.BytesIO(image_data))
            return image.size
        except Exception as e:
            raise ImageProcessingError(f"Invalid image data: {e}")
    
    async def process_artwork_image(
        self, 
        artwork: Artwork, 
        embed_metadata: bool = False,
        resize: bool = True
    ) -> bytes:
        """Process artwork image with optional metadata embedding and resizing."""
        
        if not artwork.bg_url:
            raise ImageProcessingError("Artwork has no image URL")
        
        # Download the image
        self.logger.debug(f"Downloading image for {artwork.display_name}")
        image_data = await self.download_image(artwork.bg_url)
        
        # Validate image
        width, height = self.validate_image(image_data)
        self.logger.debug(f"Image dimensions: {width}x{height}")
        
        # Resize if needed
        if resize:
            image_data = self.resize_image(image_data)
        
        # Embed metadata if requested
        if embed_metadata:
            image_data = self.embed_metadata(image_data, artwork)
            self.logger.debug(f"Embedded metadata for {artwork.display_name}")
        
        return image_data
    
    async def save_image(self, image_data: bytes, filepath: Path) -> None:
        """Save image data to file."""
        try:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'wb') as f:
                f.write(image_data)
            self.logger.debug(f"Saved image to {filepath}")
        except Exception as e:
            raise ImageProcessingError(f"Failed to save image: {e}")