"""Metadata management service for artwork collections."""

import asyncio
import json
import logging
import os
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx
from ollama import chat

from ..core.exceptions import FileOperationError, MetadataError
from ..core.models import (Artwork, ArtworkCollection, ArtworkMetadata,
                           ArtworkTranslation)


class MetadataService:
    """Service for managing artwork metadata and collections."""

    def __init__(self):
        self.logger = logging.getLogger(__name__)

    def load_collection_from_json(self, filepath: str) -> ArtworkCollection:
        """Load artwork collection from JSON file."""
        try:
            path = Path(filepath)
            if not path.exists():
                raise FileOperationError(f"JSON file not found: {filepath}")

            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            collection = ArtworkCollection(name=path.stem)

            # Handle different JSON formats
            if isinstance(data, dict):
                # Populated format: {key: artwork_data, ...}
                for key, artwork_data in data.items():
                    artwork = self._create_artwork_from_dict(artwork_data)
                    collection.artworks[key] = artwork
            elif isinstance(data, list):
                # Simple list format: [artwork_data, ...]
                for i, artwork_data in enumerate(data):
                    artwork = self._create_artwork_from_dict(artwork_data)
                    key = f"{artwork.number}" if artwork.number else str(i)
                    collection.artworks[key] = artwork

            return collection

        except json.JSONDecodeError as e:
            raise MetadataError(f"Invalid JSON format in {filepath}: {e}")
        except Exception as e:
            raise FileOperationError(f"Failed to load collection: {e}")

    def save_collection_to_json(self, collection: ArtworkCollection, filepath: str) -> None:
        """Save artwork collection to JSON file."""
        try:
            path = Path(filepath)
            path.parent.mkdir(parents=True, exist_ok=True)

            # Convert to dictionary format
            data = {}
            for key, artwork in collection.artworks.items():
                data[key] = self._artwork_to_dict(artwork)

            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            self.logger.info(f"Saved {collection.count()} artworks to {filepath}")

        except Exception as e:
            raise FileOperationError(f"Failed to save collection: {e}")

    def _create_artwork_from_dict(self, data: Dict[str, Any]) -> Artwork:
        """Create Artwork object from dictionary data."""
        try:
            # Extract metadata
            metadata = ArtworkMetadata(
                **data
            )

            return Artwork(
                number=data.get('number'),
                filename=data.get('filename'),
                bg_url=data.get('bg_url'),
                metadata=metadata
            )
        except Exception as e:
            raise MetadataError(f"Failed to create artwork from data: {e}")

    def _artwork_to_dict(self, artwork: Artwork) -> Dict[str, Any]:
        """Convert Artwork object to dictionary."""
        result = {
            'author': artwork.metadata.author,
            'title': artwork.metadata.title,
            'style': artwork.metadata.style,
            'year': artwork.metadata.year,
            'century': artwork.metadata.century,
            'location': artwork.metadata.location,
        }

        if artwork.metadata.wikipedia_url:
            result['wikipedia_url'] = artwork.metadata.wikipedia_url
        if artwork.number is not None:
            result['number'] = artwork.number
        if artwork.filename:
            result['filename'] = artwork.filename
        if artwork.bg_url:
            result['bg_url'] = artwork.bg_url

        return result

    def generate_metadata_from_images(self, images_dir: str, base_url: str) -> List[Dict[str, Any]]:
        """Generate metadata for images in a directory."""
        try:
            images_path = Path(images_dir)
            if not images_path.exists():
                raise FileOperationError(f"Images directory not found: {images_dir}")

            results = []
            number = 1

            # Walk through directory structure (max 3 levels deep)
            import os
            for root, _, files in os.walk(images_path):
                # Calculate relative path and depth
                root_path = Path(root)
                rel_path = root_path.relative_to(images_path)
                levels = len(rel_path.parts) if str(rel_path) != '.' else 0

                # Skip if too deep
                if levels > 3:
                    continue

                # Process image files
                for file in files:
                    if self._is_image_file(file):
                        filepath = root_path / file

                        # Generate metadata from path and filename
                        metadata = self._extract_metadata_from_path(
                            filepath, images_path, number, base_url
                        )
                        results.append(metadata)
                        number += 1

            self.logger.info(f"Generated metadata for {len(results)} images")
            return results

        except Exception as e:
            raise MetadataError(f"Failed to generate metadata: {e}")

    def _is_image_file(self, filename: str) -> bool:
        """Check if file is a supported image format."""
        extensions = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        return Path(filename).suffix.lower() in extensions

    def _extract_metadata_from_path(
        self, filepath: Path, base_path: Path, number: int, base_url: str
    ) -> Dict[str, Any]:
        """Extract metadata from file path structure."""
        rel_path = filepath.relative_to(base_path)
        parts = list(rel_path.parts)

        # Default values
        author = "Unknown"
        title = filepath.stem
        style = ""

        # Try to extract from path structure
        if len(parts) >= 2:
            # Format: author/title.jpg or style/author/title.jpg
            if len(parts) == 2:
                author = parts[0]
                title = Path(parts[1]).stem
            elif len(parts) >= 3:
                style = parts[0]
                author = parts[1]
                title = Path(parts[-1]).stem

        # Clean up extracted data
        author = self._clean_name(author)
        title = self._clean_name(title)
        style = self._clean_name(style)

        # Generate URL
        url_path = str(rel_path).replace('\\', '/')
        bg_url = f"{base_url.rstrip('/')}/{url_path}"

        return {
            'number': number,
            'filename': f"{number:04d}-{filepath.stem}.jpg",
            'bg_url': bg_url,
            'author': author,
            'title': title,
            'style': style,
            'year': '',
            'century': '',
            'location': '',
            'wikipedia_url': ''
        }

    def _clean_name(self, name: str) -> str:
        """Clean and format names from file paths."""
        # Replace underscores and hyphens with spaces
        cleaned = name.replace('_', ' ').replace('-', ' ')

        # Title case
        cleaned = ' '.join(word.capitalize() for word in cleaned.split())

        return cleaned

    async def populate_with_ai(
        self,
        collection: ArtworkCollection,
        ai_model: str = "llama3.2:latest",
        batch_size: int = 5
    ) -> ArtworkCollection:
        """Populate artwork metadata using AI."""
        artworks = list(collection.artworks.values())
        populated_collection = ArtworkCollection(name=f"{collection.name}_populated")

        # Process in batches
        for i in range(0, len(artworks), batch_size):
            batch = artworks[i:i + batch_size]
            self.logger.info(f"Processing batch {i//batch_size + 1} ({len(batch)} artworks)")

            tasks = [self._populate_artwork_metadata(artwork, ai_model) for artwork in batch]
            populated_artworks = await asyncio.gather(*tasks, return_exceptions=True)

            # Add successfully populated artworks
            for j, result in enumerate(populated_artworks):
                if isinstance(result, Exception):
                    self.logger.error(f"Failed to populate {batch[j].display_name}: {result}")
                    # Keep original artwork
                    original = batch[j]
                    key = f"{original.number}" if original.number else original.safe_filename
                    populated_collection.artworks[key] = original
                else:
                    # result is the populated Artwork
                    populated_artwork = result
                    key = f"{populated_artwork.number}" if populated_artwork.number else populated_artwork.safe_filename
                    populated_collection.artworks[key] = populated_artwork

        return populated_collection

    async def _populate_artwork_metadata(self, artwork: Artwork, ai_model: str) -> Artwork:
        """Populate single artwork metadata using AI."""
        try:
            prompt = f"""
            Analyze this artwork information and provide detailed metadata:

            Title: {artwork.metadata.title}
            Author: {artwork.metadata.author}
            Style: {artwork.metadata.style or 'Unknown'}

            Please provide:
            1. Corrected/full author name
            2. Complete artwork title
            3. Art movement/style
            4. Year created (if known)
            5. Century
            6. Current location (museum/gallery)
            7. Brief description

            Format as JSON with keys: author, title, style, year, century, location, description
            """

            response = chat(model=ai_model, messages=[{'role': 'user', 'content': prompt}])

            # Parse AI response
            ai_data = self._parse_ai_response(response.message.content)

            # Update metadata
            updated_metadata = ArtworkMetadata(
                author=ai_data.get('author', artwork.metadata.author),
                title=ai_data.get('title', artwork.metadata.title),
                style=ai_data.get('style', artwork.metadata.style),
                year=ai_data.get('year', artwork.metadata.year),
                century=ai_data.get('century', artwork.metadata.century),
                location=ai_data.get('location', artwork.metadata.location),
                wikipedia_url=artwork.metadata.wikipedia_url
            )

            # Create new artwork with updated metadata
            return Artwork(
                number=artwork.number,
                filename=artwork.filename,
                bg_url=artwork.bg_url,
                metadata=updated_metadata,
                binary_data=artwork.binary_data
            )

        except Exception as e:
            raise MetadataError(f"AI population failed for {artwork.display_name}: {e}")

    def _parse_ai_response(self, response: str) -> Dict[str, str]:
        """Parse AI response to extract metadata."""
        try:
            # Try to find JSON in the response
            start = response.find('{')
            end = response.rfind('}') + 1

            if start >= 0 and end > start:
                json_str = response[start:end]
                return json.loads(json_str)
            else:
                # Fallback: parse line by line
                return self._parse_text_response(response)

        except json.JSONDecodeError:
            return self._parse_text_response(response)

    def _parse_text_response(self, response: str) -> Dict[str, str]:
        """Parse plain text AI response."""
        result = {}
        lines = response.split('\n')

        for line in lines:
            line = line.strip()
            if ':' in line:
                key, value = line.split(':', 1)
                key = key.strip().lower()
                value = value.strip().strip('"\'')

                # Map common variations
                key_mapping = {
                    'artist': 'author',
                    'painter': 'author',
                    'creator': 'author',
                    'artwork': 'title',
                    'painting': 'title',
                    'movement': 'style',
                    'period': 'century',
                    'museum': 'location',
                    'gallery': 'location'
                }

                key = key_mapping.get(key, key)
                if key in {'author', 'title', 'style', 'year', 'century', 'location'}:
                    result[key] = value

        return result

    def get_random_artwork(self, collection: ArtworkCollection) -> Optional[Artwork]:
        """Get a random artwork from the collection."""
        if not collection.artworks:
            return None

        return random.choice([v for v in collection.artworks.values() if v.bg_url is not None])

    def find_duplicates(self, collection: ArtworkCollection) -> List[Artwork]:
        """Find duplicate artworks in collection."""
        seen = {}
        duplicates = []

        for artwork in collection.artworks.values():
            key = f"{artwork.metadata.title}|{artwork.metadata.author}"

            if key in seen:
                duplicates.append(artwork)
            else:
                seen[key] = artwork

        return duplicates

    def find_missing_images(self, collection: ArtworkCollection) -> List[Artwork]:
        """Find missing images."""
        missing = []

        for artwork in collection.artworks.values():
            if not os.path.exists(Path("artworks") / artwork.filename):
                missing.append(artwork)

                for old in os.listdir("artworks"):
                    if old.startswith(f"{artwork.number:04d}-"):
                        o = os.path.join("artworks", old)
                        n = os.path.join("artworks", artwork.filename)
                        print(f"Found old artwork file: {o}, new file: {n}")
                        os.rename(o, n)
                        break

        return missing

    def validate_collection(self, collection: ArtworkCollection) -> List[str]:
        """Validate collection and return list of issues."""
        issues = []
        numbers = set()

        for key, artwork in collection.artworks.items():
            # Check for missing data
            if not artwork.metadata.title or artwork.metadata.title == 'Untitled':
                issues.append(f"Missing title for artwork {key}")

            if not artwork.metadata.author or artwork.metadata.author == 'Unknown':
                issues.append(f"Missing author for artwork {key}")

            if not artwork.bg_url:
                issues.append(f"Missing image URL for artwork {key}")

            # Check for duplicate numbers
            if artwork.number:
                if artwork.number in numbers:
                    issues.append(f"Duplicate number {artwork.number} for artwork {key}")
                numbers.add(artwork.number)

        # Check for missing numbers in sequence
        if numbers:
            expected = set(range(1, max(numbers) + 1))
            missing = expected - numbers
            for num in missing:
                issues.append(f"Missing artwork number {num}")

        return issues
