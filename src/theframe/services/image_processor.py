"""Image processing service for TheFrame application."""

import asyncio
import io
import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import aiohttp
import httpx
from PIL import Image, ImageDraw, ImageFilter, ImageFont

from ..core.exceptions import ImageProcessingError
from ..core.models import Artwork, ArtworkMetadata


class ImageProcessor:
    """Service for processing artwork images."""

    def __init__(self, font_path: Optional[str] = None):
        # Load font with fallbacks
        font_paths = [
            "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
            "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",  # Linux
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Debian/Ubuntu
            "arialbd.ttf",  # Windows
        ]
        if font_path and Path(font_path).exists():
            self.font_path = font_path
        else:
            self.font_path = next((p for p in font_paths if Path(p).exists()), None)
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
            width, height = image.size

            # Ensure image is in RGB mode
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Create a semi-transparent overlay
            overlay = Image.new('RGBA', image.size, (0, 0, 0, 0))
            draw = ImageDraw.Draw(overlay)


            # Load font (use default if custom font fails)
            font_size_author = max(12, int(height * 0.02))
            font_size_title = max(14, int(height * 0.03))
            font_size_extra = max(10, int(height * 0.02))

            try:
                if self.font_path and Path(self.font_path).exists():
                    font_author = ImageFont.truetype(self.font_path, font_size_author)
                    font_title = ImageFont.truetype(self.font_path, font_size_title)
                    font_extra = ImageFont.truetype(self.font_path, font_size_extra)
                else:
                    font_author = ImageFont.load_default()
                    font_title = ImageFont.load_default()
                    font_extra = ImageFont.load_default()
            except OSError:
                font = ImageFont.load_default()

            color_author = (255, 239, 180, 255)
            color_title = (255, 255, 255, 255)
            color_extra = (90, 130, 200, 255)

            metadata = artwork.metadata.i18n.get('es')
            line_author = metadata.author
            line_title = metadata.title
            line_extra = f"{metadata.style} · {artwork.metadata.century} ({artwork.metadata.year}) · {metadata.location}"

            # Calculate text sizes using textbbox
            def get_text_size(
                text: str, font: Union[ImageFont.FreeTypeFont, ImageFont.ImageFont]
            ) -> tuple[int, int]:
                bbox = draw.textbbox((0, 0), text, font=font)
                return int(bbox[2] - bbox[0]), int(bbox[3] - bbox[1])

            try:
                text_w1, text_h1 = get_text_size(line_author, font_author)
                text_w2, text_h2 = get_text_size(line_title, font_title)
                text_w3, text_h3 = get_text_size(line_extra, font_extra)
            except Exception:
                # Fallback if text size calculation fails
                text_w1, text_h1 = len(line_author) * 8, 16
                text_w2, text_h2 = len(line_title) * 10, 20
                text_w3, text_h3 = len(line_extra) * 7, 14

            # Padding and spacing
            padding_x = 40
            padding_y = 35
            spacing = 15
            divider_height = 2
            line_space = 25

            box_width = max(text_w1, text_w2, text_w3) + 2 * padding_x
            box_height = (
                text_h1
                + 2
                + text_h2
                + divider_height
                + text_h3
                + 2 * padding_y
                + 2 * spacing
                + line_space
            )

            # Position box at bottom left with margins
            margin_x, margin_y = 50, 50
            box_x0 = margin_x
            box_y0 = height - box_height - margin_y
            box_x1 = box_x0 + box_width
            box_y1 = box_y0 + box_height

            # Ensure box is within image bounds
            box_x0 = max(0, min(box_x0, width - box_width))
            box_x1 = box_x0 + box_width
            box_y0 = max(0, min(box_y0, height - box_height))
            box_y1 = box_y0 + box_height

            # Create shadow layer
            shadow = Image.new("RGBA", image.size, (0, 0, 0, 0))
            shadow_draw = ImageDraw.Draw(shadow)
            shadow_offset = 10
            shadow_box = [
                box_x0 + shadow_offset,
                box_y0 + shadow_offset,
                box_x1 + shadow_offset,
                box_y1 + shadow_offset,
            ]
            shadow_draw.rectangle(shadow_box, fill=(0, 0, 0, 180))
            shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))

            # Draw box background
            draw.rectangle(
                [box_x0, box_y0, box_x1, box_y1],
                fill=(0, 0, 0, 140),  # Semi-transparent background
                outline=(255, 255, 255, 255),  # White border
                width=1,  # Border thickness
            )

            # Text coordinates
            text_x = box_x0 + padding_x
            text_y = box_y0 + padding_y

            # Draw author (with shadow effect)
            shadow_offset = 2
            draw.text(
                (text_x + shadow_offset, text_y + shadow_offset),
                line_author,
                font=font_author,
                fill=(0, 0, 0, 255),
            )
            draw.text((text_x, text_y), line_author, font=font_author, fill=color_author)


            # Title
            title_y = text_y + text_h1 + spacing
            draw.text(
                (text_x + shadow_offset, title_y + shadow_offset),
                line_title,
                font=font_title,
                fill=(0, 0, 0, 255),
            )
            draw.text((text_x, title_y), line_title, font=font_title, fill=color_title)

            # Divider line
            divider_y = title_y + text_h2 + line_space
            draw.rectangle(
                [
                    text_x,
                    divider_y,
                    text_x + max(text_w1, text_w2, text_w3),
                    divider_y + divider_height,
                ],
                fill=color_title,
            )

            # Extra information
            extra_y = divider_y + divider_height + spacing
            draw.text(
                (text_x + shadow_offset, extra_y + shadow_offset),
                line_extra,
                font=font_extra,
                fill=(0, 0, 0, 255),
            )
            draw.text((text_x, extra_y), line_extra, font=font_extra, fill=color_extra)


            # Compose final image
            try:
                base = Image.alpha_composite(image, shadow)
                final_image = Image.alpha_composite(base, overlay)
            except Exception:
                # Fallback if alpha composition fails
                final_image = image

            # Composite the overlay onto the original image
            image_with_overlay = Image.alpha_composite(
                image.convert('RGBA'), overlay
            ).convert('RGB')

            output = io.BytesIO()
            image_with_overlay.save(output, format='JPEG', quality=95)
            return output.getvalue()


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
