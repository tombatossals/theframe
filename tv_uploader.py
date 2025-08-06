#!/usr/bin/env python3

import os

import urllib3
from dotenv import load_dotenv
from samsungtvws import SamsungTVWS

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Cargar variables de entorno
load_dotenv()


def upload_to_tv(image_path, tv_ip):
    """Sube una imagen al TV Samsung The Frame"""
    try:
        # Crear conexión con el TV
        tv = SamsungTVWS(host=tv_ip, port=8002, token_file=os.getenv("TV_TOKEN"))

        # Leer el archivo de imagen
        with open(image_path, 'rb') as file:
            data = file.read()

        # Subir la imagen
        uploaded_id = tv.art().upload(data, file_type="JPEG", matte='none')
        tv.art().select_image(uploaded_id, show=tv.art().get_artmode() == "on")

        print(f"Imagen subida exitosamente al TV {tv_ip}")

        # Limpiar imágenes antiguas
        try:
            current_img = tv.art().get_current()
            info = tv.art().available()
            ids = [i.get("content_id") for i in info if i.get("content_id") != current_img.get("content_id")]
            tv.art().delete_list(ids)
            print("Imágenes antiguas eliminadas del TV")
        except Exception as e:
            print(f"Advertencia: No se pudieron eliminar imágenes antiguas: {e}")

        return True

    except Exception as e:
        print(f"Error subiendo imagen al TV: {e}")
        return False
