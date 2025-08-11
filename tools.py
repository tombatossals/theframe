import asyncio
import io
import json
import logging
import os
import platform
import random
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from urllib.parse import quote

import aiohttp
import httpx
import requests
from dotenv import load_dotenv
from ollama import ChatResponse, chat
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from samsungtvws import SamsungTVWS
from slugify import slugify

from _types import Background

# Load environment variables
load_dotenv()


def disable_logger(logger_name: str) -> None:
    """Disable a specific logger to reduce noise."""
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())


def generate_json(base_dir: str, base_url: str) -> List[Dict[str, Any]]:
    """Generate JSON metadata for images in a directory."""
    result = []
    base_path = Path(base_dir)

    # Use Path.walk() for more modern approach (Python 3.12+)
    try:
        # For compatibility with older Python versions
        for root, _, files in os.walk(base_dir):
            # Calculate depth
            rel_path = os.path.relpath(root, base_dir)
            levels = rel_path.split(os.sep) if rel_path != "." else []

            # Skip if more than 3 levels
            if len(levels) > 3:
                continue

            for file in files:
                if file.lower().endswith(
                    (".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp")
                ):
                    absolute_path = os.path.join(root, file)
                    relative_path = os.path.relpath(absolute_path, base_dir)
                    url_path = quote(relative_path.replace(os.sep, "/"))
                    url = f"{base_url}/{url_path}"

                    data = os.path.basename(os.path.splitext(file)[0]).split("-")
                    author = data[0].strip()
                    title = data[1].strip() if len(data) > 1 else author

                    result.append(
                        {
                            "filename": file,
                            "title": title,
                            "author": author,
                            "file_size": os.path.getsize(absolute_path),
                            "file_type": os.path.splitext(file)[1].lower(),
                            "url": url,
                        }
                    )
    except Exception as e:
        logging.error(f"Error generating JSON from {base_dir}: {e}")
        return []

    # Remove duplicates while preserving order
    seen = set()
    final = []
    for paint in result:
        key = (paint.get("author"), paint.get("title"))
        if key not in seen:
            seen.add(key)
            final.append(paint)

    logging.debug(f"Generated JSON with {len(final)} images from {base_dir}")
    return final


def embed_metadata(image: Background, test: bool = False) -> bytes:
    """Embed metadata into an image."""
    disable_logger("PIL")
    disable_logger("PIL.Image")

    image_binary = image.get("binary")
    if image_binary is None:
        raise ValueError("Image binary data is None")

    try:
        pil_image = Image.open(io.BytesIO(image_binary)).convert("RGBA")
    except Exception as e:
        logging.error(f"Error opening image: {e}")
        raise

    metadata = image.get("metadata", {})
    width, height = pil_image.size

    # Create overlay for drawing
    overlay = Image.new("RGBA", pil_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Load font with fallbacks
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",  # macOS
        "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",  # Linux
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",  # Debian/Ubuntu
        "arialbd.ttf",  # Windows
    ]

    font_path = None
    for path in font_paths:
        if os.path.exists(path):
            font_path = path
            break

    if not font_path:
        # Fallback to default font
        font_author = ImageFont.load_default()
        font_title = ImageFont.load_default()
        font_extra = ImageFont.load_default()
    else:
        try:
            font_size_author = max(12, int(height * 0.02))
            font_size_title = max(14, int(height * 0.03))
            font_size_extra = max(10, int(height * 0.02))

            font_author = ImageFont.truetype(font_path, font_size_author)
            font_title = ImageFont.truetype(font_path, font_size_title)
            font_extra = ImageFont.truetype(font_path, font_size_extra)
        except Exception:
            # Fallback to default font if truetype fails
            font_author = ImageFont.load_default()
            font_title = ImageFont.load_default()
            font_extra = ImageFont.load_default()

    color_author = (255, 239, 180, 255)
    color_title = (255, 255, 255, 255)
    color_extra = (90, 130, 200, 255)

    # Text to display
    line_author = str(metadata.get("author", "Unknown"))
    line_title = str(metadata.get("title", "Unknown"))
    line_extra = f"Style {metadata.get('style', 'Unknown style')} · {metadata.get('century', 'Unknown century')} ({metadata.get('year', 'Unknown year')}) · {metadata.get('location', 'Unknown location')}"

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
    shadow = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))
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
        base = Image.alpha_composite(pil_image, shadow)
        final_image = Image.alpha_composite(base, overlay)
    except Exception:
        # Fallback if alpha composition fails
        final_image = pil_image

    buffer = io.BytesIO()
    try:
        final_image.convert("RGB").save(buffer, format="JPEG", quality=95)
    except Exception as e:
        logging.error(f"Error saving image: {e}")
        # Try with default parameters
        final_image.convert("RGB").save(buffer, format="JPEG")

    if test:
        try:
            final_image.convert("RGB").save("test.jpg", format="JPEG", quality=95)
        except Exception:
            final_image.convert("RGB").save("test.jpg", format="JPEG")

    return buffer.getvalue()


async def fetch_image_data(url: str) -> bytes:
    """Asynchronously fetch image data from a URL."""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                response.raise_for_status()
                return await response.read()
    except Exception as e:
        logging.error(f"Error fetching image data from {url}: {e}")
        raise


def pick_random_image(
    populated_json: str, embed: bool = False, test: bool = False
) -> Optional[Background]:
    """Pick a random image from the populated JSON."""
    try:
        populated_path = Path(populated_json)
        if not populated_path.exists():
            logging.error(f"Populated JSON file not found: {populated_json}")
            return None

        with open(populated_json, "r", encoding="utf-8") as f:
            populated = json.load(f)

        # Filter images with bg_url
        selected_images = [i for i in populated.values() if i.get("bg_url")]
        if not selected_images:
            logging.error("No images with bg_url found in the JSON.")
            return None

        selected_image = random.choice(selected_images)

        # Fetch image data with timeout
        try:
            with httpx.Client(timeout=30.0) as client:
                response = client.get(selected_image.get("bg_url"))
                response.raise_for_status()
                image_data = response.content
        except httpx.RequestError as e:
            logging.error(
                f"Error fetching image from {selected_image.get('bg_url')}: {e}"
            )
            return None
        except httpx.HTTPStatusError as e:
            logging.error(f"HTTP error {e.response.status_code} fetching image: {e}")
            return None

        logging.debug(
            f"Fetched image: {selected_image.get('author', 'Unknown')} - {selected_image.get('title', 'Unknown')}"
        )

        # Extract metadata
        metadata = selected_image.get("languages", {}).get("es", {})
        bgimage: Background = {
            "metadata": {
                "author": metadata.get("author", "Unknown"),
                "style": metadata.get("style", "Unknown"),
                "year": metadata.get("year", "Unknown"),
                "century": metadata.get("century", "Unknown"),
                "location": metadata.get("location", "Unknown"),
                "title": metadata.get("title", "Unknown"),
                "wikipedia_url": metadata.get("wikipedia_url", ""),
            },
            "binary": image_data,
            "number": selected_image.get("number"),
            "filename": selected_image.get("filename"),
            "bg_url": selected_image.get("bg_url"),
        }

        if embed:
            bgimage["binary"] = embed_metadata(bgimage, test=test)

        return bgimage

    except json.JSONDecodeError as e:
        logging.error(f"Error parsing JSON file {populated_json}: {e}")
        return None
    except Exception as e:
        logging.error(f"Error picking random image: {e}")
        return None


def upload_to_tv(
    image: Background, tv_ip: str, tv_token: str, tv_port: int = 8002
) -> None:
    """Upload an image to the Samsung TV."""
    try:
        logging.debug(f"Connecting to TV at {tv_ip}:{tv_port} with token {tv_token}")
        disable_logger("samsungtvws")

        tv = SamsungTVWS(host=tv_ip, port=tv_port, token=tv_token, timeout=10)
        uploaded_id = tv.art().upload(image["binary"], file_type="JPEG", matte="none")
        tv.art().select_image(uploaded_id, show=tv.art().get_artmode() == "on")
        logging.info(f"Uploaded image: {image['metadata'].get('title', 'Unknown')}")

        # Delete old images (optional cleanup)
        try:
            current_img = tv.art().get_current()
            info = tv.art().available()
            ids = [
                i.get("content_id")
                for i in info
                if i.get("content_id") != current_img.get("content_id")
            ]
            if ids:
                logging.debug(f"Deleting old images: {ids}")
                tv.art().delete_list(ids)
        except Exception as e:
            logging.debug(f"Note: Could not clean up old images: {e}")

    except Exception as e:
        logging.error(f"Error uploading image to TV: {e}")
        raise


def get_full_name(name: str) -> str:
    """Convert a name from 'Last, First' to 'First Last' format."""
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name


def get_incremental_pending_name(path_str: str) -> str:
    """Get the name for the incremental pending file."""
    path = Path(path_str)
    if path.suffix.lower() != ".json":
        raise ValueError("File must end in .json")

    filename = path.with_suffix("")  # Remove .json
    filename = filename.with_name(filename.name + ".incremental.pending.json")
    return str(filename)


def get_incremental_completed_name(path_str: str) -> str:
    """Get the name for the incremental completed file."""
    path = Path(path_str)
    if path.suffix.lower() != ".json":
        raise ValueError("File must end in .json")

    filename = path.with_suffix("")  # Remove .json
    filename = filename.with_name(filename.name + ".incremental.completed.json")
    return str(filename)


def url_exists(url: str) -> bool:
    """Check if a URL exists."""
    disable_logger("requests")
    disable_logger("urllib3")
    try:
        response = requests.head(url, allow_redirects=True, timeout=10)
        result: bool = response.status_code == 200
        return result
    except requests.RequestException as e:
        logging.debug(f"URL check failed for {url}: {e}")
        return False


def get_next_number(completed: Dict[str, Any], current_index: int) -> int:
    """Get the next available number for a painting."""
    existing_numbers = [
        v.get("number") for v in completed.values() if isinstance(v.get("number"), int)
    ]
    return max(existing_numbers, default=0) + current_index + 1


def populate(
    destination_json: str, paintings: List[Dict[str, Any]], base_url: str
) -> Dict[str, Any]:
    """Populate artwork metadata."""
    disable_logger("httpx")
    disable_logger("httpcore")
    disable_logger("asyncio")

    # System prompt for AI metadata enrichment
    system_prompt = """
You are an expert in art history and museum cataloging.

Your task is to normalize and complete artwork metadata from a minimal input JSON.

ALWAYS return a valid JSON with all fields filled, including their corresponding information translated in Spanish, with no additional text.

In the translated section, normalize author names to their canonical Spanish form.

If multiple versions of an artwork exist, prioritize the canonical or best-documented version and specify its current museum location.

Fill missing fields with the best available evidence; if there is reasonable doubt, choose the most well-supported data from museums or reference catalogs and maintain historical consistency.

Required output format:
{
"title": "...",
"author": "...",
"style": "...",
"year": "...",
"century": "...",
"location": "...",
"wikipedia_url": "...",
"languages": {
    "es": {
        "title": "...",
        "author": "...",
        "style": "...",
        "year": "...",
        "century": "...",
        "location": "..."
    }
}
}

Rules:
title: In english, title without year or notes.
author: normalized author name, in english.
style: In english, style or movement (e.g., Venetian Renaissance, Mannerism, High Renaissance). Use the most accepted term for that specific work.
year: most accepted execution year for the prioritized version (numeric or brief range if appropriate).
century: century in Roman numerals (e.g., XVI).
location: In english, museum, city, country.
wikipedia_url: English Wikipedia URL of this painting.

Do not include comments or explanations outside the JSON.

User instructions:
Input:
{
"title_and_author": "{title}"
}

Return the enriched JSON.

Implementation notes:
If the input contains an ambiguous year (e.g., "1542" in the title), do not carry it over to the "year" field if it does not match the prioritized version; use the most accepted year for the canonical version (for Venus y Adonis, Prado 1554).
If the user wants a different policy (e.g., prioritize a specific museum's version), add an optional "preferred_location" parameter in the input and adapt the selection accordingly.
For works with multiple versions (e.g., variants in the Getty or NGA), if no preference is provided, prioritize the best-documented or primary academic reference version; for Venus y Adonis, the Prado version with the precise 1554 date is commonly the reference.
"""

    completed: Dict[str, Any] = dict()
    populated: Dict[str, Any] = dict()
    updated = False

    # Load existing completed data
    destination_path = Path(destination_json)
    if destination_path.exists():
        try:
            with open(destination_json, "r", encoding="utf-8") as f:
                completed = json.load(f)
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing existing JSON file {destination_json}: {e}")
            completed = dict()

    # Load incremental completed data
    incremental_completed_path = get_incremental_completed_name(destination_json)
    if Path(incremental_completed_path).exists():
        try:
            with open(incremental_completed_path, "r", encoding="utf-8") as f:
                n = json.load(f)
                if n:  # Check if dict is not empty
                    updated = True

                # Merge with completed, preferring completed entries that have bg_url
                for key in list(n.keys()):
                    if completed.get(key, {}).get("bg_url"):
                        del n[key]
                completed = {**completed, **n}
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing incremental completed JSON: {e}")

    # Count completed paintings
    pending = [i for i in completed.values() if i.get("bg_url") is not None]
    logging.debug(
        f"Found {len(pending)}/{len(completed)} completed paintings in {destination_json}"
    )

    # If we have new paintings to process
    if paintings:
        for painting in paintings:
            title = painting.get("name", "Unknown")
            key = f"new-{slugify(title)}"
            completed[key] = {"title": title}
        return completed

    # Update bg_url for existing entries if missing
    for painting in completed.values():
        # Remove deprecated fields
        if "image_url" in painting:
            del painting["image_url"]

        # Add bg_url if missing and file exists
        if painting.get("bg_url") is None and painting.get("filename"):
            url = f"{base_url}/{painting['filename']}"
            if url_exists(url):
                painting["bg_url"] = url
                updated = True

    # If we updated anything, return early
    if updated:
        return completed

    # Process pending paintings with AI enrichment
    pending_paintings: List[Dict[str, Any]] = []
    newdata: Dict[str, Any] = dict()

    incremental_pending_path = get_incremental_pending_name(destination_json)
    if Path(incremental_pending_path).exists():
        try:
            with open(incremental_pending_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    pending_paintings = data
                else:
                    logging.error(f"Expected list in pending file, got {type(data)}")
                    pending_paintings = []
        except json.JSONDecodeError as e:
            logging.error(f"Error parsing incremental pending JSON: {e}")
            pending_paintings = []

    # Process each pending painting
    processed_indices = []
    for i, painting in enumerate(pending_paintings):
        try:
            title = painting.get("name", "Unknown")
            logging.debug(f"Populating data: {title}...")

            # Get AI enrichment
            response: ChatResponse = chat(
                model="gpt-oss:20b",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f'{{"title_and_author": "{title}"}}'},
                ],
            )

            # Parse AI response
            content = response.message.content or ""
            answer = json.loads(content.strip())
            answer["number"] = get_next_number(completed, i)
            answer["filename"] = (
                f"{str(answer.get('number')).zfill(4)}-{slugify(answer.get('author'))}-{slugify(answer.get('title'))}.jpg"
            )

            # Check if image file exists
            if url_exists(f"{base_url}/{answer.get('filename')}"):
                answer["bg_url"] = f"{base_url}/{answer.get('filename')}"
            else:
                answer["bg_url"] = None

            newdata[answer.get("filename")] = answer
            processed_indices.append(i)

            logging.debug(f"Done. ({i + 1}/{len(pending)}) {answer.get('filename')}")

        except json.JSONDecodeError as e:
            logging.error(f"Error parsing AI response for {painting.get('name')}: {e}")
            continue
        except Exception as e:
            logging.error(f"Error processing {painting.get('name')}: {e}")
            continue

    # Update pending and completed files
    if processed_indices:
        # Remove processed items from pending
        for i in sorted(processed_indices, reverse=True):
            if i < len(pending):
                pending.pop(i)

        # Save updated pending file
        try:
            with open(incremental_pending_path, "w", encoding="utf-8") as f:
                json.dump(pending, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving pending file: {e}")

        # Save completed data
        try:
            with open(incremental_completed_path, "w", encoding="utf-8") as f:
                json.dump(newdata, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logging.error(f"Error saving completed file: {e}")

    return completed


def find_duplicates(paintings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Find duplicate paintings in a list."""
    seen: Counter[tuple[str, str]] = Counter()
    duplicates: List[Dict[str, Any]] = []
    for painting in paintings:
        # Create a unique identifier for the painting
        title = painting.get("title", "") or ""
        author = painting.get("author", "") or ""
        identifier = (title.lower().strip(), author.lower().strip())
        seen[identifier] += 1
        if seen[identifier] > 1:
            duplicates.append(painting)
    return duplicates
