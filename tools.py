import io
import json
import logging
import os
import platform
import random
import urllib.request
from urllib.parse import quote

from dotenv import load_dotenv
from PIL import Image, ImageDraw, ImageFilter, ImageFont
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
                title = data[1].strip() if len(data) > 1 else author

                result.append({
                    "filename": file,
                    "title": title,
                    "author": author,
                    "file_size": os.path.getsize(ruta_absoluta),
                    "file_type": os.path.splitext(file)[1].lower(),
                    "url": url
                })

    paintings = set()
    final = list()
    for paint in result:
        key = (paint.get("author"), paint.get("title"))
        if key not in paintings:
            paintings.add(key)
            final.append(paint)

    logging.debug(f"Generated JSON with {len(final)} images from {base_dir}")
    return final

def embed_metadata(image: Background) -> bytes:
    logging.getLogger("pil").setLevel(logging.ERROR)  # Reduce PIL logging noise
    pil_image = Image.open(io.BytesIO(image.get("binary"))).convert("RGBA")
    metadata = image.get("metadata", {})
    _, height = pil_image.size

    # Crear capa para dibujo
    overlay = Image.new("RGBA", pil_image.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(overlay)

    # Cargar fuente
    if platform.system() == "Darwin":
        font_path = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
    else:
        font_path = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"

    font_size_author = int(height * 0.025)
    font_size_title = int(height * 0.03)

    font_author = ImageFont.truetype(font_path, font_size_author)
    font_title = ImageFont.truetype(font_path, font_size_title)

    # Texto a mostrar
    line_author = f"{metadata.get('author', 'Unknown')}"
    line_title = f"{metadata.get('title', 'Unknown')}"

    # Calcular tamaños de texto usando textbbox
    def get_text_size(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    text_w1, text_h1 = get_text_size(line_author, font_author)
    text_w2, text_h2 = get_text_size(line_title, font_title)

    # Padding
    padding_x = 40
    padding_y = 35
    spacing = 15
    divider_height = 2
    line_space = 25

    box_width = max(text_w1, text_w2) + 2 * padding_x
    box_height = (
        text_h1 + divider_height + text_h2 +
        2 * padding_y + spacing + line_space
    )

    box_x0 = 50
    box_y0 = height - box_height - 50
    box_x1 = box_x0 + box_width
    box_y1 = box_y0 + box_height


    # Crear capa sombra
    shadow = Image.new("RGBA", pil_image.size, (0, 0, 0, 0))
    shadow_draw = ImageDraw.Draw(shadow)
    offset = 10
    shadow_box = [box_x0 + offset, box_y0 + offset, box_x1 + offset, box_y1 + offset]
    shadow_draw.rectangle(shadow_box, fill=(0, 0, 0, 180))
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=10))

    # Dibujar caja y texto **antes** de componer capas
    draw.rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        fill=(0, 0, 0, 140),
        outline=(255, 255, 255, 255),
        width=1
    )

    # 4. Componer sombra + caja + texto
    base = Image.alpha_composite(pil_image, shadow)



    # Dibujar caja con sombra (más oscura)
    draw.rectangle(
        [box_x0, box_y0, box_x1, box_y1],
        fill=(0, 0, 0, 140),            # Fondo semitransparente
        outline=(255, 255, 255, 255),  # Borde blanco
        width=1                        # Grosor del borde
    )

    # Coordenadas de texto
    text_x = box_x0 + padding_x
    text_y = box_y0 + padding_y

    # Dibujar autor (sombra y texto)
    shadow_offset = 2
    draw.text((text_x + shadow_offset, text_y + shadow_offset), line_author, font=font_author, fill=(0, 0, 0, 255))
    draw.text((text_x, text_y), line_author, font=font_author, fill=(255, 255, 255, 255))

    # Línea divisoria
    divider_y = text_y + text_h1 + line_space
    draw.rectangle(
        [text_x, divider_y, text_x + max(text_w1, text_w2), divider_y + divider_height],
        fill=(255, 255, 255, 255)
    )

    # Título
    title_y = divider_y + divider_height + spacing
    draw.text((text_x + shadow_offset, title_y + shadow_offset), line_title, font=font_title, fill=(0, 0, 0, 255))
    draw.text((text_x, title_y), line_title, font=font_title, fill=(255, 255, 255, 255))

    # Componer imagen final
    buffer = io.BytesIO()
    final_image = Image.alpha_composite(base, overlay)
    final_image.convert("RGB").save(buffer, format="JPEG", quality=95)
    #final_image.convert("RGB").save("test.jpg", format="JPEG", quality=95)

    return buffer.getvalue()

def pick_random_image(source_json_url, embed=False) -> Background:
        with urllib.request.urlopen(source_json_url) as response:
            raw_data = response.read()
            decoded = raw_data.decode('utf-8')
            images = json.loads(decoded)

        selected_image = random.choice(images)
        image_url = selected_image['url']

        with urllib.request.urlopen(image_url) as img_response:
            image_data = img_response.read()


        logging.debug(f"Fetched image: {selected_image.get('author', 'Unknown')} - {selected_image.get('title', 'Unknown')}")

        bgimage = {
            "metadata": {
                "filename": selected_image.get('filename', 'unknown.jpg'),
                "url": image_url,
                "author": selected_image.get('author', 'Unknown'),
                "title": selected_image.get('title', 'Unknown'),
                "file_size": selected_image.get('file_size', 0),
                "file_type": selected_image.get('file_type', 'unknown')
            },
            "binary": image_data
        }

        if embed:
            bgimage['binary'] = embed_metadata(bgimage)

        return bgimage


def upload_to_tv(image, tv_ip, tv_token, tv_port=8002, timeout=5):

    try:
        logging.debug(f"Conectando a TV en {tv_ip}:{tv_port} con token {tv_token}")
        logger = logging.getLogger("samsungtvws").setLevel(logging.INFO)

        tv = SamsungTVWS(host=tv_ip, port=tv_port, token=tv_token)
        uploadedID = tv.art().upload(image.get("binary"), file_type="JPEG", matte='none')
        tv.art().select_image(uploadedID, show=tv.art().get_artmode() == "on")
        logging.debug(f"Uploaded image: {image.get('metadata', {}).get('title', 'Unknown')}")

        # Delete old images
        try:
            current_img = tv.art().get_current()
            ids = [ i.get("content_id") for i in info if i.get("content_id") != current_img.get("content_id")]
            logging.debug(f"Deleting old images: {ids}")
            tv.art().delete_list(ids)
        except Exception as e:
            return

    except Exception as e:
        logging.error(f"Error al subir la imagen a la TV: {e}")


