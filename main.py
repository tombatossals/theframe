#!/usr/bin/env python3

import argparse
import json
import logging
import os
import sys

from dotenv import load_dotenv

from tools import (find_duplicates, generate_json, pick_random_image, populate,
                   upload_to_tv)

# Load environment variables
load_dotenv()



def main():
    parser = argparse.ArgumentParser(description='Image manager for Samsung The Frame TV')

    # Parameters
    parser.add_argument('--ip', help='Samsung TV device IP address (optional if THEFRAME_IP is in .env)')
    parser.add_argument('--source', help='JSON URL with available images (optional if BACKGROUNDS_SOURCE is in .env)')
    parser.add_argument('--embed', action='store_true', help='Embed metadata in the image before uploading')
    parser.add_argument('--token', help='Samsung TV Token (optional if THEFRAME_TOKEN is in .env)')

    parser.add_argument('--paintings_json', help='JSON FILE to write the generated images (optional if PAINTINGS_JSON is in .env)')
    parser.add_argument('--painters_json', help='JSON FILE to write the generated images (optional if PAINTERS_JSON is in .env)')
    parser.add_argument('--populated_json', help='JSON FILE to write the generated images (optional if POPULATED_JSON is in .env)')

    parser.add_argument('--images_dir', help='Directory with images to process (optional if IMAGES_DIR is in .env)')
    parser.add_argument('--base_url', help='Base URL for the images (optional if BASE_URL is in .env)')

    parser.add_argument('command', choices=['upload', 'generate', 'populate', 'errors'], help='Command to execute')

    parser.add_argument('--debug', action='store_true', default=False, help='Log debug messages')

    parser.add_argument('--test', action='store_true', default=False, help='Only for testing purposes, saves the final image as test.jpg')

    parser.add_argument('--increment', action='store_true', default=False, help='Add 10 paintings to the collection')

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

        populated_json = args.populated_json or os.getenv('POPULATED_JSON')
        if not populated_json:
            print("Error: Debe especificar el archivo de destino con --populated_json o configurar POPULATED_JSON en el archivo .env")
            sys.exit(1)

        # Determine image source: command line argument or environment variable
        backgrounds_source = args.source or os.getenv('SOURCE_JSON')
        if not backgrounds_source:
            print("Error: Debe especificar la URL del JSON con --source o configurar SOURCE en el archivo .env")
            sys.exit(1)


        logging.debug("Fetching random image from source...")
        image = pick_random_image(populated_json, embed=args.embed, test=args.test)
        if not image:
            logging.error("No se pudo obtener una imagen del origen especificado.")
            sys.exit(1)

        if not args.test:
            upload_to_tv(image, tv_ip, tv_token)

    elif args.command == 'generate':

        paintings_json = args.paintings_json or os.getenv('PAINTINGS_JSON')
        if not paintings_json:
            print("Error: Debe especificar el archivo de destino con --paintings_json o configurar PAINTINGS_JSON en el archivo .env")
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
        with open(paintings_json, 'w', encoding='utf-8') as f:
            json.dump(images, f, ensure_ascii=False, indent=2)

    elif args.command == 'populate':
        paintings_json = args.paintings_json or os.getenv('PAINTINGS_JSON')
        if not paintings_json:
            print("Error: Debe especificar el archivo de destino con --paintings_json o configurar PAINTINGS_JSON en el archivo .env")
            sys.exit(1)

        populated_json = args.populated_json or os.getenv('POPULATED_JSON')
        if not populated_json:
            print("Error: Debe especificar el archivo de destino con --populated_json o configurar POPULATED_JSON en el archivo .env")
            sys.exit(1)

        base_url = args.base_url or os.getenv('BASE_URL')
        if not base_url:
            print("Error: Debe especificar la URL base con --base_url o configurar BASE_URL en el archivo .env")
            sys.exit(1)

        paintings = []
        finished_paintings = []
        increment = args.increment
        with open(paintings_json, 'r', encoding='utf-8') as f:
            p = json.load(f)[0:10]
            paintings = p[0:10]
            finished_paintings = p[10:] if len(p) > 10 else []

        populated = populate(populated_json, paintings, base_url,)
        with open(populated_json, 'w', encoding='utf-8') as f:
            json.dump(populated, f, ensure_ascii=False, indent=2)

        if increment and len(finished_paintings) > 0:
            with open(paintings_json, "w", encoding="utf-8") as f:
                json.dump(finished_paintings, f, ensure_ascii=False, indent=2)

    elif args.command == 'errors':
        populated_json = args.populated_json or os.getenv('POPULATED_JSON')
        if not populated_json:
            print("Error: Debe especificar el archivo de destino con --populated_json o configurar POPULATED_JSON en el archivo .env")
            sys.exit(1)

        with open(populated_json, 'r', encoding='utf-8') as f:
            populated = json.load(f)
            numbers = set()
            for painting in populated.values():
                if painting.get("number") in numbers:
                    logging.error(f"Duplicated: {painting.get('number')} - {painting.get('title', 'Unknown')} - {painting.get('author', 'Unknown')}")
                numbers.add(painting.get("number"))

                if str(painting.get("number")).zfill(4) != painting.get("filename").split("-")[0]:
                    logging.error(f"Filename mismatch: {painting.get('number')} - {painting.get('title', 'Unknown')} - {painting.get('author', 'Unknown')}")
                if not painting.get("bg_url"):
                    logging.warning(f"Missing bg_url: {painting.get('number')} - {painting.get('title', 'Unknown')} - {painting.get('author', 'Unknown')}")

            missing = set(range(1, len(numbers) + 1)) - numbers
            for m in missing:
                logging.error(f"Missing painting: {m}")

            duplicates = find_duplicates(list(populated.values()))
            for dup in duplicates:
                logging.error(f"Duplicate painting found: {dup.get('title', 'Unknown')} - {dup.get('author', 'Unknown')}")

    else:
        print("Comando no reconocido. Use 'upload', 'generate' o 'populate'.")
        sys.exit(1)

if __name__ == "__main__":
    main()
