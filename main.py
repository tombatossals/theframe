#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv

from tools import generate_json, pick_random_image, upload_to_tv

# Load environment variables
load_dotenv()



def main():
    parser = argparse.ArgumentParser(description='Image manager for Samsung The Frame TV')

    # Parameters
    parser.add_argument('--ip', help='Samsung TV device IP address (optional if THEFRAME_IP is in .env)')
    parser.add_argument('--source', help='JSON URL with available images (optional if BACKGROUNDS_SOURCE is in .env)')
    parser.add_argument('--embed', action='store_true', help='Embed metadata in the image before uploading')
    parser.add_argument('--token', help='Samsung TV Token (optional if THEFRAME_TOKEN is in .env)')

    parser.add_argument('--destination', help='JSON FILE to write the generated images (optional if DESTINATION_JSON is in .env)')
    parser.add_argument('--images_dir', help='Directory with images to process (optional if IMAGES_DIR is in .env)')
    parser.add_argument('--base_url', help='Base URL for the images (optional if BASE_URL is in .env)')

    parser.add_argument('command', choices=['upload', 'generate'], help='Command to execute')
    parser.add_argument('--debug', action='store_true', default=False, help='Log debug messages')

    args = parser.parse_args()

    log_level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(level=log_level, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

    # Execute according to command
    if args.command == 'upload':
        # Determine IP to use: command line argument or environment variable
        tv_ip = args.ip or os.getenv('THEFRAME_IP')

        if not tv_ip:
            print("Error: Debe especificar la IP del TV con --ip o configurar IP en el archivo .env")
            sys.exit(1)

        # If token is provided, use it; otherwise, use the one from .env
        tv_token = args.token or os.getenv('THEFRAME_TOKEN')

        if not tv_token:
            print("Error: Debe especificar el token del TV con --token o configurar THEFRAME_TOKEN en el archivo .env")
            sys.exit(1)
        # Determine image source: command line argument or environment variable
        backgrounds_source = args.source or os.getenv('SOURCE_JSON')

        if not backgrounds_source:
            print("Error: Debe especificar la URL del JSON con --source o configurar SOURCE en el archivo .env")
            sys.exit(1)


        logging.debug("Fetching random image from source...")
        image = pick_random_image(backgrounds_source, embed_metadata=args.embed)
        logging.debug(f"Image fetched: {image.get('metadata', {}).get('name', 'Unknown')}")
        upload_to_tv(image, tv_ip, tv_token)
    elif args.command == 'generate':

        destination_json = args.destination or os.getenv('DESTINATION_JSON')
        if not destination_json:
            print("Error: Debe especificar el archivo de destino con --destination o configurar DESTINATION_JSON en el archivo .env")
            sys.exit(1)

        images_dir = args.images_dir or os.getenv('IMAGES_DIR')
        if not images_dir:
            print("Error: Debe especificar el directorio de imágenes con --images_dir o configurar IMAGES_DIR en el archivo .env")
            sys.exit(1)

        base_url = args.base_url or os.getenv('BASE_URL')
        if not base_url:
            print("Error: Debe especificar la URL base con --base_url o configurar BASE_URL en el archivo .env")
            sys.exit(1)

        # Generate the JSON
        images = generate_json(images_dir, base_url)

        # Save to disk (optional)
        with open(destination_json, 'w', encoding='utf-8') as f:
            json.dump(images, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
