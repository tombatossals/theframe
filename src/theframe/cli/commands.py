"""CLI commands for TheFrame application."""

import json
import os
from pathlib import Path
from typing import Any, Optional

import requests
from slugify import slugify

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
        collection = metadata_service.load_collection_from_json(self.settings.artworks_json)

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

class PopulateCommand(BaseCommand):
    """Populate artwork metadata with AI enhancement."""

    def get_artwork_info(self, author_title: str) -> dict | None:
        """
        Dado un pintor y el nombre (aproximado) de una obra,
        devuelve información estructurada en formato JSON.
        """

        url = os.getenv("AI_BASE_URL")
        headers = {
            "Authorization": f"Bearer {os.getenv('AI_API_KEY')}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "sonar-pro",
            "messages": [
                {
                    "role": "user",
                    "content": f"""
        Dado el siguiente pintor y una obra (puede tener errores ortográficos),
        devuelve un JSON con la siguiente estructura:

        {{
            "author": <AUTHOR>,
            "title": <TITLE>,
            "style": <STYLE>,
            "year": <YEAR>,
            "century": <CENTURY en números romanos>,
            "location": <LOCATION>,
            "wikipedia_url": <WIKIPEDIA_URL>,
            "i18n": {{
                "es": {{
                    "author": <AUTHOR_ES>,
                    "title": <TITLE_ES>,
                    "style": <STYLE_ES>,
                    "location": <LOCATION_ES>
                }}
            }}
        }}

        Pintor y título aproximado: "{author_title}"

        IMPORTANTE:
        - Corrige el título si está mal escrito o incompleto, devolviendo el más parecido posible.
        - El siglo debe ir en números romanos (ej. XIX, XVII).
        - Responde ÚNICAMENTE con el JSON válido, sin explicaciones adicionales.
        - Evita incluir código Markdown indicando que es JSON en la respuesta.
        """
                }
            ]
        }

        response = requests.post(url, headers=headers, json=payload)

        try:
            r = response.json()
        except Exception:
            print("⚠️ La API no devolvió JSON válido. Respuesta cruda:")
            print(response.text[:500])
            return None

        content = r.get("choices", [{}])[0].get("message", {}).get("content")
        if not content:
            print("⚠️ No se encontró contenido en la respuesta:", r)
            return None

        try:
            return json.loads(content)
        except json.JSONDecodeError:
            print("⚠️ El modelo devolvió algo que no es JSON válido:")
            print(content)
            return None

    def next_number(self, directory):
        numbers = []
        for file in os.listdir(directory):
            if file[:4].isdigit():
                numbers.append(int(file[:4]))
        if not numbers:
            return 1  # Si no hay archivos, empieza en 1

        return max(numbers) + 1

    def validate_settings(self) -> None:
        """Validate settings for populate command."""
        self.settings.validate_for_populate()

    async def execute(self) -> None:
        """Execute populate command."""
        metadata_service = MetadataService()

        # Load existing collection
        source = json.loads(Path(self.settings.source_json).read_text(encoding="utf-8"))
        for a in source[:1]:
            author_title = a.get("name")

            result = self.get_artwork_info(author_title)
            number = self.next_number("json")

            if not result:
                continue  # saltar si no hubo respuesta válida

            result["number"] = number
            author_title = result.get("author") + " - " + result.get("title")
            print(result)

            filename = os.path.join(
                "./json",
                str(number).zfill(4) + "-" + slugify(author_title) + ".json"
            )

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"Guardado en {filename}")

            out = source[1:]
            with open(self.settings.source_json, 'w', encoding='utf-8') as f:
                json.dumps(out, ensure_ascii=False, indent=2)

class ErrorsCommand(BaseCommand):
    """Check for errors in artwork metadata."""

    def validate_settings(self) -> None:
        """Validate settings for errors command."""
        if not self.settings.artworks_json:
            raise ConfigurationError(
                "Artworks JSON path is required for errors command",
                "Set THEFRAME_ARTWORKS_JSON environment variable or use --artworks-json"
            )

    async def execute(self) -> None:
        """Execute errors command."""
        metadata_service = MetadataService()

        # Load collection
        collection = metadata_service.load_collection_from_json(self.settings.artworks_json)

        # Find duplicates
        duplicates = metadata_service.find_duplicates(collection)
        if duplicates:
            self.logger.error("Found duplicate artworks:")
            for artwork in duplicates:
                self.logger.error(f"{artwork.display_name}")

        # Check missing images
        missing = metadata_service.find_missing_images(collection)
        if missing:
            self.logger.error("Found missing images:")
            for artwork in missing:
                self.logger.error(f"{artwork.filename}")

        # Validate collection
        issues = metadata_service.validate_collection(collection)
        if issues:
            self.logger.error("Validation issues found:")
            for issue in issues:
                self.logger.error(f"{issue}")

        if not duplicates and not issues:
            self.logger.info("No errors found in collection")
        else:
            self.logger.info(f"Found {len(duplicates)} duplicates and {len(issues)} issues")

class GenerateJsonCommand(BaseCommand):
    """Generate JSON file from artwork metadata."""

    def validate_settings(self) -> None:
        """Validate settings for generate_json command."""
        if not self.settings.artworks_json:
            raise ConfigurationError(
                "Artworks JSON path is required for generate_json command",
                "Set THEFRAME_ARTWORKS_JSON environment variable or use --artworks-json"
            )

    async def execute(self) -> None:
        """Execute generate_json command."""
        metadata_service = MetadataService()

        json_path = Path(__file__).parent / ".." / ".." / ".." / "json"

        artworks = {}
        for f in sorted(json_path.glob("*.json")):
            with open(f, "r", encoding="utf-8") as json_file:
                data = json.load(json_file)
                artworks[f.name] = data

        with open(os.getenv("THEFRAME_ARTWORKS_JSON"), "w", encoding="utf-8") as json_file:
            json.dump(artworks, json_file, ensure_ascii=False, indent=2)

        self.logger.info(f"Generated JSON file at {json_path}")

