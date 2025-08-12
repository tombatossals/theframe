#!/usr/bin/env python3

import argparse
import json
import logging
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from rich.logging import RichHandler

from tools import (find_duplicates, generate_json,
                   get_incremental_completed_name,
                   get_incremental_pending_name, pick_random_image, populate,
                   upload_to_tv)

# Load environment variables
load_dotenv()


class Config(BaseSettings):
    """Configuration model for the application."""

    model_config = SettingsConfigDict(env_prefix="THEFRAME_")

    ip: Optional[str] = None
    token: Optional[str] = None
    source_json: Optional[str] = None
    paintings_json: Optional[str] = None
    painters_json: Optional[str] = None
    populated_json: Optional[str] = None
    images_dir: Optional[str] = None
    base_url: Optional[str] = None


def setup_logging(debug: bool = False) -> None:
    """Set up logging with rich formatting."""
    log_level = logging.DEBUG if debug else logging.ERROR
    logging.basicConfig(
        level=log_level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True)],
    )


def validate_file_path(file_path: str, env_var: str) -> str:
    """Validate that a file path exists."""
    if not file_path:
        raise ValueError(
            f"Must specify file path with --{env_var.lower()} or configure THEFRAME_{env_var.upper()} in .env file"
        )

    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    return str(path)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Image manager for Samsung The Frame TV",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""commands:
  upload    Upload a random image to your TV
  generate  Generate artwork metadata from image files
  populate  Populate artwork metadata with AI enrichment
  errors    Check for errors in artwork metadata
""",
    )

    # Parameters
    parser.add_argument("--ip", help="Samsung TV device IP address")
    parser.add_argument("--source", help="JSON URL with available images")
    parser.add_argument(
        "--embed",
        action="store_true",
        help="Embed metadata in the image before uploading",
    )
    parser.add_argument("--token", help="Samsung TV Token")

    parser.add_argument(
        "--paintings-json", help="JSON FILE to write the generated images"
    )
    parser.add_argument(
        "--painters-json", help="JSON FILE to write the generated images"
    )
    parser.add_argument(
        "--populated-json", help="JSON FILE to write the populated images"
    )

    parser.add_argument("--images-dir", help="Directory with images to process")
    parser.add_argument("--base-url", help="Base URL for the images")

    parser.add_argument(
        "command",
        choices=["upload", "generate", "populate", "errors"],
        help="Command to execute",
    )

    parser.add_argument("--debug", action="store_true", help="Log debug messages")
    parser.add_argument(
        "--test",
        action="store_true",
        help="Only for testing purposes, saves the final image as test.jpg",
    )
    parser.add_argument(
        "--increment",
        action="store_true",
        help="Add paintings to the collection incrementally",
    )

    args = parser.parse_args()

    setup_logging(args.debug)

    # Load configuration
    config = Config()

    # Execute according to command
    if args.command == "upload":
        # Determine IP to use: command line argument or environment variable
        tv_ip = args.ip or config.ip

        if not tv_ip:
            logging.error(
                "Error: Must specify the TV IP with --ip or configure THEFRAME_IP in the .env file"
            )
            sys.exit(1)

        # If token is provided, use it; otherwise, use the one from config
        tv_token = args.token or config.token

        if not tv_token:
            logging.error(
                "Error: Must specify the TV token with --token or configure THEFRAME_TOKEN in the .env file"
            )
            sys.exit(1)

        populated_json = args.populated_json or config.populated_json
        if not populated_json:
            logging.error(
                "Error: Must specify the destination file with --populated-json or configure POPULATED_JSON in the .env file"
            )
            sys.exit(1)

        logging.debug("Fetching random image from source...")
        image = pick_random_image(populated_json, embed=args.embed, test=args.test)
        if not image:
            logging.error("Could not get an image from the specified source.")
            sys.exit(1)

        if not args.test:
            upload_to_tv(image, tv_ip, tv_token)

    elif args.command == "generate":
        paintings_json = args.paintings_json or config.paintings_json
        if not paintings_json:
            logging.error(
                "Error: Must specify the destination file with --paintings-json or configure THEFRAME_PAINTINGS_JSON in the .env file"
            )
            sys.exit(1)

        images_dir = args.images_dir or config.images_dir
        if not images_dir:
            logging.error(
                "Error: Must specify the images directory with --images-dir or configure THEFRAME_IMAGES_DIR in the .env file"
            )
            sys.exit(1)

        base_url = args.base_url or config.base_url
        if not base_url:
            logging.error(
                "Error: Must specify the base URL with --base-url or configure THEFRAME_BASE_URL in the .env file"
            )
            sys.exit(1)

        # Generate the JSON
        images = generate_json(images_dir, base_url)

        # Save to disk
        with open(paintings_json, "w", encoding="utf-8") as f:
            json.dump(images, f, ensure_ascii=False, indent=2)

        logging.info(
            f"Generated JSON with {len(images)} images saved to {paintings_json}"
        )

    elif args.command == "populate":
        paintings_json = args.paintings_json or config.paintings_json
        if not paintings_json:
            logging.error(
                "Error: Must specify the paintings file with --paintings-json or configure THEFRAME_PAINTINGS_JSON in the .env file"
            )
            sys.exit(1)

        populated_json = args.populated_json or config.populated_json
        if not populated_json:
            logging.error(
                "Error: Must specify the populated file with --populated-json or configure THEFRAME_POPULATED_JSON in the .env file"
            )
            sys.exit(1)

        base_url = args.base_url or config.base_url
        if not base_url:
            logging.error(
                "Error: Must specify the base URL with --base-url or configure THEFRAME_BASE_URL in the .env file"
            )
            sys.exit(1)

        paintings: List[Dict[str, Any]] = []
        finished_paintings: List[Dict[str, Any]] = []
        increment = args.increment

        if increment:
            with open(paintings_json, "r", encoding="utf-8") as f:
                p = json.load(f)
                paintings = p[0:2]
                finished_paintings = p[2:] if len(p) > 2 else []

                with open(
                    get_incremental_pending_name(populated_json), "w", encoding="utf-8"
                ) as f:
                    json.dump(paintings, f, ensure_ascii=False, indent=2)

                if len(finished_paintings) > 0:
                    with open(paintings_json, "w", encoding="utf-8") as f:
                        json.dump(finished_paintings, f, ensure_ascii=False, indent=2)
        else:
            populated = populate(populated_json, paintings, base_url)
            with open(populated_json, "w", encoding="utf-8") as f:
                json.dump(populated, f, ensure_ascii=False, indent=2)

            with open(
                get_incremental_completed_name(populated_json), "r", encoding="utf-8"
            ) as f:
                data = json.load(f)
                for k in [k for k in data.keys() if k in populated.keys()]:
                    data.pop(k, None)

                with open(
                    get_incremental_completed_name(populated_json),
                    "w",
                    encoding="utf-8",
                ) as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

    elif args.command == "errors":
        populated_json = args.populated_json or config.populated_json
        if not populated_json:
            logging.error(
                "Error: Must specify the populated file with --populated-json or configure THEFRAME_POPULATED_JSON in the .env file"
            )
            sys.exit(1)

        with open(populated_json, "r", encoding="utf-8") as f:
            populated = json.load(f)
            numbers = set()
            for painting in reversed(
                [v for v in populated.values() if v.get("filename")]
            ):
                if painting.get("number") in numbers:
                    logging.error(
                        f"Duplicated: {painting.get('number')} - {painting.get('title', 'Unknown')} - {painting.get('author', 'Unknown')}"
                    )
                numbers.add(painting.get("number"))

                if (
                    str(painting.get("number")).zfill(4)
                    != painting.get("filename").split("-")[0]
                ):
                    logging.error(
                        f"Filename mismatch: {painting.get('number')} - {painting.get('title', 'Unknown')} - {painting.get('author', 'Unknown')}"
                    )
                if not painting.get("bg_url"):
                    logging.warning(
                        f"Missing bg_url: {painting.get('number')} - {painting.get('title', 'Unknown')} - {painting.get('author', 'Unknown')}"
                    )

            missing = set(range(1, len(numbers) + 1)) - numbers
            for m in missing:
                logging.error(f"Missing painting: {m}")

            duplicates = find_duplicates(
                [v for v in populated.values() if v.get("filename")]
            )
            for dup in duplicates:
                logging.error(
                    f"Duplicate painting found: {dup.get('title', 'Unknown')} - {dup.get('author', 'Unknown')}"
                )

    else:
        logging.error(
            "Unrecognized command. Use 'upload', 'generate', 'populate', or 'errors'."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
