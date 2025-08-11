import io
import json
import logging
import os
import platform
import random
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from ollama import ChatResponse, chat
from PIL import Image, ImageDraw, ImageFilter, ImageFont
from samsungtvws import SamsungTVWS
from slugify import slugify

from _types import Background


def disable_logger(logger_name):
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.CRITICAL)
    logger.propagate = False
    logger.handlers.clear()
    logger.addHandler(logging.NullHandler())


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

def embed_metadata(image: Background, test=False) -> bytes:
    disable_logger("PIL")
    disable_logger("PIL.image")

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

    font_size_author = int(height * 0.02)
    font_size_title = int(height * 0.03)
    font_size_extra = int(height * 0.02)

    font_author = ImageFont.truetype(font_path, font_size_author)
    font_title = ImageFont.truetype(font_path, font_size_title)
    font_extra = ImageFont.truetype(font_path, font_size_extra)

    color_author =(255, 239, 180, 255)
    color_title = (255, 255, 255, 255)
    color_extra = (90, 130, 200, 255)

    # Texto a mostrar
    line_author = f"{metadata.get('author', 'Unknown')}"
    line_title = f"{metadata.get('title', 'Unknown')}"
    line_extra = f"Estilo {metadata.get('style', 'Estilo desconocido')} · {metadata.get('century', 'Siglo desconocido')} ({metadata.get('year', 'Año desconocido')}) · {metadata.get('location', 'Ubicación desconocida')}"

    # Calcular tamaños de texto usando textbbox
    def get_text_size(text, font):
        bbox = draw.textbbox((0, 0), text, font=font)
        return bbox[2] - bbox[0], bbox[3] - bbox[1]

    text_w1, text_h1 = get_text_size(line_author, font_author)
    text_w2, text_h2 = get_text_size(line_title, font_title)
    text_w3, text_h3 = get_text_size(line_extra, font_extra)

    # Padding
    padding_x = 40
    padding_y = 35
    spacing = 15
    divider_height = 2
    line_space = 25

    box_width = max(text_w1, text_w2, text_w3) + 2 * padding_x
    box_height = (
        text_h1 + 2 + text_h2 + divider_height+ text_h3 + 2 * padding_y +
        2 * spacing + line_space
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
    draw.text((text_x, text_y), line_author, font=font_author, fill=color_author)

    # Título
    title_y = text_y + text_h1 + spacing
    draw.text((text_x + shadow_offset, title_y + shadow_offset), line_title, font=font_title, fill=(0, 0, 0, 255))
    draw.text((text_x, title_y), line_title, font=font_title, fill=color_title)

    # Línea divisoria
    divider_y = title_y + text_h2 + line_space
    draw.rectangle(
        [text_x, divider_y, text_x + max(text_w1, text_w2, text_w3), divider_y + divider_height],
        fill=color_title
    )

    # Extra
    extra_y = divider_y + divider_height + spacing
    draw.text((text_x + shadow_offset, extra_y + shadow_offset), line_extra, font=font_extra, fill=(0, 0, 0, 255))
    draw.text((text_x, extra_y), line_extra, font=font_extra, fill=color_extra)

    # Componer imagen final
    buffer = io.BytesIO()
    final_image = Image.alpha_composite(base, overlay)
    final_image.convert("RGB").save(buffer, format="JPEG", quality=95)

    if test:
        final_image.convert("RGB").save("test.jpg", format="JPEG", quality=95)

    return buffer.getvalue()

def pick_random_image(populated_json, embed=False, test=False) -> Background:
        with open(populated_json, 'r', encoding='utf-8') as f:
            populated = json.load(f)

        selected_image = random.choice([ i for i in populated.values() if i.get("bg_url")])

        if not selected_image:
            logging.error(f"No se encontró la imagen {r} en el JSON de origen.")
            return None

        with urllib.request.urlopen(selected_image.get("bg_url")) as img_response:
            image_data = img_response.read()


        logging.debug(f"Fetched image: {selected_image.get('author', 'Unknown')} - {selected_image.get('title', 'Unknown')}")

        metadata = selected_image.get("languages").get("es")
        bgimage = {
            "metadata": {
                "filename": selected_image.get('filename', 'unknown.jpg'),
                "url": selected_image.get("bg_url"),
                "author": metadata.get('author', 'Unknown'),
                "style": metadata.get('style', 'Unknown'),
                "year": metadata.get('year', 'Unknown'),
                "century": metadata.get('century', 'Unknown'),
                "location": metadata.get('location', 'Unknown'),
                "title": metadata.get('title', 'Unknown')
            },
            "binary": image_data
        }

        if embed:
            bgimage['binary'] = embed_metadata(bgimage, test=test)

        return bgimage


def upload_to_tv(image, tv_ip, tv_token, tv_port=8002, timeout=5):

    try:
        logging.debug(f"Conectando a TV en {tv_ip}:{tv_port} con token {tv_token}")
        disable_logger("samsungtvws")

        tv = SamsungTVWS(host=tv_ip, port=tv_port, token=tv_token)
        uploadedID = tv.art().upload(image.get("binary"), file_type="JPEG", matte='none')
        tv.art().select_image(uploadedID, show=tv.art().get_artmode() == "on")
        logging.debug(f"Uploaded image: {image.get('metadata', {}).get('title', 'Unknown')}")

        # Delete old images
        try:
            current_img = tv.art().get_current()
            info = tv.art().available()
            ids = [ i.get("content_id") for i in info if i.get("content_id") != current_img.get("content_id")]
            logging.debug(f"Deleting old images: {ids}")
            tv.art().delete_list(ids)
        except Exception as e:
            logging.error(f"Error deleting old images", e)
            return

    except Exception as e:
        logging.error(f"Error al subir la imagen a la TV: {e}")

def get_full_name(name: str) -> str:
    parts = [p.strip() for p in name.split(",")]
    if len(parts) == 2:
        return f"{parts[1]} {parts[0]}"
    return name

def get_incremental_name(path_str: str) -> str:
    p = Path(path_str)
    if p.suffix.lower() != ".json":
        raise ValueError("El archivo debe terminar en .json")

    filename = p.with_suffix("") # quita .json
    filename = filename.with_name(filename.name + ".incremental.json")
    return str(filename)

def url_exists(url: str) -> bool:
    disable_logger("requests")
    disable_logger("urllib3")
    try:
        respuesta = requests.head(url, allow_redirects=True, timeout=5)
        return respuesta.status_code == 200
    except requests.RequestException:
        return False

def populate(destination_json, paintings, base_url):
    disable_logger("httpx")
    disable_logger("httpcore")
    disable_logger("asyncio")

    prompt = """
    System instructions:

You are an expert in art history and museum cataloging.

Your task is to normalize and complete artwork metadata from a minimal input JSON.

ALWAYS return a valid JSON with all fields filled, including their corresponding information translated in Spanish, with no additional text.

In the translated section, normalize author names to their canonical Spanish form.

If multiple versions of an artwork exist, prioritize the canonical or best-documented version and specify its current museum location.

Fill missing fields with the best available evidence; if there is reasonable doubt, choose the most well-supported data from museums or reference catalogs and maintain historical consistency.

Required output format:
{{
"title": "...",
"author": "...",
"style": "...",
"year": "...",
"century": "...",
"location": "...",
"wikipedia_url": "...",
"languages": {{
    "es": {{
        "title": "...",
        "author": "...",
        "style": "...",
        "year": "...",
        "century": "...",
        "location": "..."
    }}
}}
}}

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
{{
"title_and_author": "{title}"
}}

Return the enriched JSON.

Implementation notes:

If the input contains an ambiguous year (e.g., “1542” in the title), do not carry it over to the “year” field if it does not match the prioritized version; use the most accepted year for the canonical version (for Venus y Adonis, Prado 1554).

If the user wants a different policy (e.g., prioritize a specific museum’s version), add an optional “preferred_location” parameter in the input and adapt the selection accordingly.

For works with multiple versions (e.g., variants in the Getty or NGA), if no preference is provided, prioritize the best-documented or primary academic reference version; for Venus y Adonis, the Prado version with the precise 1554 date is commonly the reference."""

    completed = dict()
    populated = dict()

    if os.path.exists(destination_json):
        with open(destination_json, 'r', encoding='utf-8') as f:
            completed = json.load(f)

    if os.path.exists(get_incremental_name(destination_json)):
        with open(get_incremental_name(destination_json), 'r', encoding='utf-8') as f:
            n = json.load(f)
            for clave in list(n.keys()):
                if completed.get(clave, {}).get("bg_url"):
                    del n[clave]
            completed = { **completed, **n }

    pending = [i for i in completed.values() if i.get("bg_url") is not None]
    logging.debug(f"Found {len(pending)}/{len(completed)} completed paintings in {destination_json}")

    if len(paintings) > 0:
        for i, painting in enumerate(paintings):
            title = painting.get('name')
            completed[f"new-{slugify(title)}"] = {
                "title": title
            }
        return completed

    updated = False
    for i, painting in enumerate(completed.values()):
        if painting.get("image_url"):
            del painting["image_url"]

        if painting.get("bg_url") == None and url_exists(f"{base_url}/{painting.get('filename')}"):
            painting["bg_url"] = f"{base_url}/{painting.get('filename')}"
            updated = True

    if updated:
        return completed

    for i, painting in enumerate(completed.values()):
        if painting.get("filename") is None:
            logging.debug(f"Populating data: {title}...")
            response: ChatResponse = chat(model='gpt-oss:20b', messages=[
            {
                'role': 'user',
                'content': prompt.format(
                    title=title
                )
            }])

            answer = json.loads(response.message.content.strip())
            answer["number"] = i
            answer["filename"] = f"{str(i+1).zfill(4)}-{slugify(answer.get('author'))}-{slugify(answer.get('title'))}.jpg"
            if url_exists(f"{base_url}/{answer.get('filename')}"):
                answer["bg_url"] = f"{base_url}/{answer.get('filename')}"
            else:
                answer["bg_url"] = None
            populated[answer.get("filename")] = answer

            logging.debug(f"Done. ({i + 1}/{len(paintings)}) {answer.get('filename')}")

            with open(get_incremental_name(destination_json), "w") as f:
                json.dump(populated, f, ensure_ascii=False, indent=2)
                f.flush()
                os.fsync(f.fileno())


    return completed

def find_duplicates(paintings):
    seen = Counter()
    duplicates = []
    for painting in paintings:
        identifier = (painting['title'], painting['author'])
        seen[identifier] += 1
        if seen[identifier] > 1:
            duplicates.append(painting)
    return duplicates
