"""CLI commands for TheFrame application."""

import asyncio
import logging
from pathlib import Path
from typing import Any, Optional

from ..core.exceptions import ConfigurationError, TVConnectionError
from ..core.models import TVDevice
from ..services.image_processor import ImageProcessor
from ..services.metadata_service import MetadataService
from ..services.tv_service import TVService
from .base import BaseCommand


class UploadCommand(BaseCommand):
    """Upload random artwork to Samsung Frame TV."""

    def validate_settings(self) -> None:
        """Validate settings for upload command."""
        self.settings.validate_for_upload()

    async def execute(self, embed: bool = False, test: bool = False) -> None:
        """Execute upload command."""
        # Load artwork collection
        metadata_service = MetadataService()
        collection = metadata_service.load_collection_from_json(self.settings.populated_json)

        if collection.count() == 0:
            raise ConfigurationError("No artworks found in collection")

        # Get random artwork
        artwork = metadata_service.get_random_artwork(collection)
        if not artwork:
            raise ConfigurationError("Failed to select random artwork")

        self.logger.info(f"Selected: {artwork.display_name}")

        # Process image
        image_processor = ImageProcessor()
        image_data = await image_processor.process_artwork_image(
            artwork, embed_metadata=embed, resize=True
        )

        if test:
            # Save test image instead of uploading
            test_path = Path("test.jpg")
            await image_processor.save_image(image_data, test_path)
            self.logger.info(f"Test image saved as {test_path}")
        else:
            # Upload to TV
            tv_device = TVDevice(ip=self.settings.tv_ip, token=self.settings.tv_token)
            tv_service = TVService(tv_device)

            filename = artwork.safe_filename
            success = tv_service.upload_image(image_data, filename)

            if success:
                self.logger.info(f"Successfully uploaded {filename} to TV")
            else:
                raise TVConnectionError("Upload failed")

class UpdateCommand(BaseCommand):
    """Update populated with new backgrounds."""
    pass
    def validate_settings(self) -> None:
        """Validate settings for generate command."""
        self.settings.validate_for_generate()

    async def execute(self) -> None:
        """Execute generate command."""
        metadata_service = MetadataService()

        # Load existing collection
        populated_collection = metadata_service.load_collection_from_json(self.settings.populated_json)

        # Full population with AI
        self.logger.info(f"Updating collection backgrounds...")

        updated = False
        # Update bg_url for existing entries if missing
        for artwork in populated_collection.artworks.values():
            # Add bg_url if missing and file exists
            if artwork.bg_url is None and artwork.filename:
                url = f"{self.settings.base_url}/{artwork.filename}"
                if self.url_exists(url):
                    self.logger.info(f"Found new image...")
                    artwork.bg_url = url
                    updated = True

        if updated:
            # Save populated collection
            metadata_service.save_collection_to_json(
                populated_collection, self.settings.populated_json
            )

            self.logger.info(f"Populated collection saved to {self.settings.populated_json}")

class GenerateCommand(BaseCommand):
    """Generate artwork metadata from image directory."""

    def validate_settings(self) -> None:
        """Validate settings for generate command."""
        self.settings.validate_for_generate()

    async def execute(self) -> None:
        """Execute generate command."""
        metadata_service = MetadataService()

        # Generate metadata from images
        artwork_data = metadata_service.generate_metadata_from_images(
            self.settings.images_dir, self.settings.base_url
        )

        if not artwork_data:
            raise ConfigurationError("No images found in directory")

        # Save to JSON file
        import json
        output_path = Path(self.settings.paintings_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(artwork_data, f, ensure_ascii=False, indent=2)

        self.logger.info(f"Generated metadata for {len(artwork_data)} artworks")
        self.logger.info(f"Saved to {output_path}")


class PopulateCommand(BaseCommand):
    """Populate artwork metadata with AI enhancement."""

    def validate_settings(self) -> None:
        """Validate settings for populate command."""
        self.settings.validate_for_populate()

    async def execute(self, increment: bool = False) -> None:
        """Execute populate command."""
        metadata_service = MetadataService()

        # Load existing collection
        collection = metadata_service.load_collection_from_json(self.settings.populated_json)

        if increment:
            # Load existing collection
            new_collection = metadata_service.load_collection_from_json(self.settings.paintings_json)

            # Process incrementally (first 2 items)
            artworks = list(new_collection.artworks.items())
            if len(artworks) > 2:
                # Take first 2 for processing
                pending_items = dict(artworks[:2])
                remaining_items = dict(artworks[2:])

                # Save pending items
                pending_collection = collection.__class__(name="pending")
                pending_collection.artworks = pending_items

                pending_path = self.settings.populated_json.replace(".json", ".incremental.pending.json")
                metadata_service.save_collection_to_json(pending_collection, pending_path)

                # Update main collection with remaining items
                collection.artworks = remaining_items
                metadata_service.save_collection_to_json(collection, self.settings.paintings_json)

                self.logger.info(f"Prepared {len(pending_items)} artworks for incremental processing")
            else:
                self.logger.info("Not enough artworks for incremental processing")


class ErrorsCommand(BaseCommand):
    """Check for errors in artwork metadata."""

    def validate_settings(self) -> None:
        """Validate settings for errors command."""
        if not self.settings.populated_json:
            raise ConfigurationError(
                "Populated JSON path is required for errors command",
                "Set THEFRAME_POPULATED_JSON environment variable or use --populated-json"
            )

    async def execute(self) -> None:
        """Execute errors command."""
        metadata_service = MetadataService()

        # Load collection
        collection = metadata_service.load_collection_from_json(self.settings.populated_json)

        # Find duplicates
        duplicates = metadata_service.find_duplicates(collection)
        if duplicates:
            self.logger.error("Found duplicate artworks:")
            for artwork in duplicates:
                self.logger.error(f"  - {artwork.display_name}")

        # Validate collection
        issues = metadata_service.validate_collection(collection)
        if issues:
            self.logger.error("Validation issues found:")
            for issue in issues:
                self.logger.error(f"  - {issue}")

        if not duplicates and not issues:
            self.logger.info("No errors found in collection")
        else:
            self.logger.info(f"Found {len(duplicates)} duplicates and {len(issues)} issues")
