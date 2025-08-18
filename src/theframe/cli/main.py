"""Main CLI interface for TheFrame application."""

import argparse
import sys
from typing import Dict, Type

from ..core.config import get_settings, setup_logging
from ..core.exceptions import TheFrameError
from .commands import (ErrorsCommand, GenerateCommand, PopulateCommand,
                       UpdateCommand, UploadCommand)


def create_parser() -> argparse.ArgumentParser:
    """Create and configure argument parser."""
    parser = argparse.ArgumentParser(
        description="TheFrame: Samsung Frame TV artwork manager",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Commands:
  upload    Upload a random artwork to your Samsung Frame TV
  generate  Generate artwork metadata from image files
  populate  Populate artwork metadata with AI enrichment
  errors    Check for errors and duplicates in artwork metadata

Examples:
  theframe upload --ip 192.168.1.100 --token abc123
  theframe generate --images-dir ./art --base-url http://example.com/images
  theframe populate --ai-model llama3.2:latest
  theframe errors --populated-json ./data/populated.json
        """
    )

    # Global options
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging"
    )

    # TV Configuration
    parser.add_argument(
        "--ip", dest="tv_ip",
        help="Samsung TV IP address (or set THEFRAME_TV_IP)"
    )
    parser.add_argument(
        "--token", dest="tv_token",
        help="Samsung TV authentication token (or set THEFRAME_TV_TOKEN)"
    )

    # File paths
    parser.add_argument(
        "--paintings-json",
        help="Path to paintings JSON file (or set THEFRAME_PAINTINGS_JSON)"
    )
    parser.add_argument(
        "--populated-json",
        help="Path to populated JSON file (or set THEFRAME_POPULATED_JSON)"
    )
    parser.add_argument(
        "--images-dir",
        help="Directory containing images (or set THEFRAME_IMAGES_DIR)"
    )

    # URLs
    parser.add_argument(
        "--base-url",
        help="Base URL for images (or set THEFRAME_BASE_URL)"
    )

    # Command-specific options
    parser.add_argument(
        "--embed", action="store_true",
        help="Embed metadata in image before uploading (upload command)"
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Save test image instead of uploading (upload command)"
    )
    parser.add_argument(
        "--increment", action="store_true",
        help="Process artworks incrementally (populate command)"
    )

    # Command
    parser.add_argument(
        "command",
        choices=["upload", "update", "generate", "populate", "errors"],
        help="Command to execute"
    )

    return parser


def override_settings_from_args(settings, args) -> None:
    """Override settings with command line arguments."""
    if args.tv_ip:
        settings.tv_ip = args.tv_ip
    if args.tv_token:
        settings.tv_token = args.tv_token
    if args.paintings_json:
        settings.paintings_json = args.paintings_json
    if args.populated_json:
        settings.populated_json = args.populated_json
    if args.images_dir:
        settings.images_dir = args.images_dir
    if args.base_url:
        settings.base_url = args.base_url
    if args.debug:
        settings.log_level = "DEBUG"


def main() -> None:
    """Main CLI entry point."""
    parser = create_parser()
    args = parser.parse_args()

    try:
        # Load settings
        settings = get_settings()

        # Override with command line arguments
        override_settings_from_args(settings, args)

        # Setup logging
        setup_logging(settings)

        # Command mapping
        commands: Dict[str, Type] = {
            "upload": UploadCommand,
            "generate": GenerateCommand,
            "populate": PopulateCommand,
            "update": UpdateCommand,
            "errors": ErrorsCommand,
        }

        # Get command class
        command_class = commands[args.command]
        command = command_class(settings)

        # Execute command with appropriate arguments
        if args.command == "upload":
            command.run(embed=args.embed, test=args.test)
        elif args.command == "populate":
            command.run(increment=args.increment)
        else:
            command.run()

    except TheFrameError as e:
        print(f"Error: {e.message}", file=sys.stderr)
        if e.details:
            print(f"Details: {e.details}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
