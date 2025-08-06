#!/usr/bin/env python3

import argparse
import os
import sys

from dotenv import load_dotenv

from image_processor import process_image
from lib.tools import generate_json
from tv_uploader import upload_to_tv

# Load environment variables
load_dotenv()


def main():
    parser = argparse.ArgumentParser(description='Image manager for Samsung The Frame TV')

    # Parameters
    parser.add_argument('--ip', help='Samsung TV device IP address (optional if THEFRAME_IP is in .env)')
    parser.add_argument('--source', help='JSON URL with available images (optional if BACKGROUNDS_SOURCE is in .env)')
    parser.add_argument('--destination', help='JSON FILE to write the generated images (optional if DESTINATION_JSON is in .env)')
    parser.add_argument('--images_dir', help='Directory with images to process (optional if IMAGES_DIR is in .env)')
    parser.add_argument('--base_url', help='Base URL for the images (optional if BASE_URL is in .env)')

    parser.add_argument('--convert', action='store_true', help='Convert/process the image before uploading')
    parser.add_argument('command', choices=['upload', 'generate'], help='Command to execute')

    args = parser.parse_args()


    # Execute according to command
    if args.command == 'upload':
        # Determine IP to use: command line argument or environment variable
        tv_ip = args.ip or os.getenv('THEFRAME_IP')

        if not tv_ip:
            print("Error: Debe especificar la IP del TV con --ip o configurar IP en el archivo .env")
            sys.exit(1)

        # Determine image source: command line argument or environment variable
        backgrounds_source = args.source or os.getenv('SOURCE_JSON')

        if not backgrounds_source:
            print("Error: Debe especificar la URL del JSON con --source o configurar SOURCE en el archivo .env")
            sys.exit(1)


        print(f"Obteniendo imágenes desde: {backgrounds_source}")
        print(f"TV destino: {tv_ip}")
        print(f"Procesar imagen: {'Sí' if args.convert else 'No'}")

        # For now we show the configuration
        print("¡Configuración completada! (Implementación pendiente)")

        # Example of what would come:
        # selected_image = get_random_image_from_json(backgrounds_source)
        # downloaded_image = download_image(selected_image)
        #
        # if args.convert:
        #     downloaded_image = process_image(downloaded_image)
        #
        # success = upload_to_tv(downloaded_image, tv_ip)
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
            json.dump(destination_json, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
