import json
import logging
import os
import random
import urllib.request
from urllib.parse import quote

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFont
from samsungtvws import SamsungTVWS

from bgtypes import Background


def generate_json(base_dir, base_url):
    result = []
    for root, _, files in os.walk(base_dir):
        # Calcular profundidad
        rel_path = os.path.relpath(root, base_dir)
        niveles = rel_path.split(os.sep) if rel_path != "." else []

        # Saltar si hay más de 3 niveles
        if len(niveles) > 3:
            continue

        for file in files:
            if file.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')):
                ruta_absoluta = os.path.join(root, file)
                ruta_relativa = os.path.relpath(ruta_absoluta, base_dir)
                ruta_url = quote(ruta_relativa.replace(os.sep, '/'))
                url = f"{base_url}/{ruta_url}"

                data = os.path.basename(os.path.splitext(file)[0]).split("-")
                author = data[0].strip()
                name = data[1].strip() if len(data) > 1 else author

                result.append({
                    "filename": file,
                    "author": author,
                    "name": name,
                    "file_size": os.path.getsize(ruta_absoluta),
                    "file_type": os.path.splitext(file)[1].lower(),
                    "url": url,
                    "level1": niveles[0] if len(niveles) > 0 else None,
                    "level2": niveles[1] if len(niveles) > 1 else None,
                    "level3": niveles[2] if len(niveles) > 2 else None
                })

    logging.debug(f"Generated JSON with {len(result)} images from {base_dir}")
    return result

def embed_metadata(image, metadata):

    pil_image = Image.open(io.BytesIO(image_data))

    # Crear un objeto de dibujo
    draw = ImageDraw.Draw(pil_image)

    # Configurar la fuente (asegúrate de que la fuente exista en tu sistema)
    # Cambia la ruta según tu sistema
    font_path = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
    font_size = 96
    font = ImageFont.truetype(font_path, font_size)

    # Obtener el tamaño de la imagen
    image_width, image_height = pil_image.size

    # Calcular las dimensiones del texto usando textbbox
    text_bbox = draw.textbbox((0, 0), "test", font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Calcular la posición para centrar el texto en la parte baja
    text_x = (image_width - text_width) // 2
    text_y = image_height - text_height - 80  # 10 px de margen inferior

    # Dibujar un rectángulo como fondo del texto (opcional)
    margin = 20
    draw.rectangle(
        [text_x - margin, text_y, text_x +
            text_width + margin, text_y + text_height + margin + 10],
        fill="black",
    )

    # Dibujar el texto
    draw.text((text_x, text_y), metadata, font=font, fill="white")
    buffer = io.BytesIO()
    pil_image.save(buffer, format="JPEG")
    return buffer.getvalue()

def pick_random_image(source_json_url, embed_metadata=False) -> Background:
    """Selecciona una imagen aleatoria de un JSON de imágenes desde una URL y la devuelve en formato binario"""
    try:
        with urllib.request.urlopen(source_json_url) as response:
            raw_data = response.read()
            decoded = raw_data.decode('utf-8')
            images = json.loads(decoded)

        selected_image = random.choice(images)
        image_url = selected_image['url']

        with urllib.request.urlopen(image_url) as img_response:
            image_data = img_response.read()

        if embed_metadata:
            return embed_metadata(image_data, selected_image['metadata'])

        return {
            "metadata": {
                "filename": selected_image.get('filename', 'unknown.jpg'),
                "url": image_url,
                "author": selected_image.get('author', 'Unknown'),
                "name": selected_image.get('name', 'Unknown'),
                "file_size": selected_image.get('file_size', 0),
                "file_type": selected_image.get('file_type', 'unknown'),
                "level1": selected_image.get('level1', None),
                "level2": selected_image.get('level2', None),
                "level3": selected_image.get('level3', None)
            },
            "binary": image_data
        }

    except Exception as e:
        logging.error(f"Error al seleccionar imagen: {e}")
        return None

def upload_to_tv(image_data, tv_ip, tv_token, tv_port=8002, timeout=5):

    try:
        logging.debug(f"Conectando a TV en {tv_ip}:{tv_port} con token {tv_token}")
        tv = SamsungTVWS(host=tv_ip, port=tv_port, token=tv_token)
        info = tv.art().get_artmode()
        logging.debug(info)

        uploadedID = tv.art().upload(image_data, file_type="JPEG", matte='none')
        tv.art().select_image(uploadedID, show=tv.art().get_artmode() == "on")

        print(f"Imagen subida con ID: {uploadedID}")

        # Delete old images
        try:
            current_img = tv.art().get_current()
        except Exception as e:
            pass

        info = tv.art().available()
        print(info)
        ids = [ i.get("content_id") for i in info if i.get("content_id") != current_img.get("content_id")]
        tv.art().delete_list(ids)

    except Exception:
        logging.error(f"Error al conectar con el TV en {tv_ip}:{tv_port}")
        return False


