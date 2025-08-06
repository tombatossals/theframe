#!/usr/bin/env python3

import os

from PIL import Image, ImageDraw, ImageFont


def process_image(image_path, output_path=None):
    """Procesa una imagen añadiendo el nombre del archivo como texto en la parte inferior"""
    try:
        # Abrir la imagen
        image = Image.open(image_path)

        # Crear un objeto de dibujo
        draw = ImageDraw.Draw(image)

        # Obtener el nombre del archivo sin la ruta
        file_name = os.path.basename(image_path).replace(".jpg", "").replace(".jpeg", "").replace(".png", "")

        # Configurar la fuente
        font_path = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
        font_size = 96

        # Verificar si existe la fuente, si no usar la por defecto
        try:
            font = ImageFont.truetype(font_path, font_size)
        except OSError:
            # Usar fuente por defecto si no encuentra la especificada
            font = ImageFont.load_default()

        # Obtener el tamaño de la imagen
        image_width, image_height = image.size

        # Calcular las dimensiones del texto
        text_bbox = draw.textbbox((0, 0), file_name, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]

        # Calcular la posición para centrar el texto en la parte baja
        text_x = (image_width - text_width) // 2
        text_y = image_height - text_height - 80

        # Dibujar un rectángulo como fondo del texto
        margin = 20
        draw.rectangle(
            [text_x - margin, text_y, text_x + text_width + margin, text_y + text_height + margin + 10],
            fill="black",
        )

        # Dibujar el texto
        draw.text((text_x, text_y), file_name, font=font, fill="white")

        # Guardar la imagen procesada
        if output_path is None:
            output_path = os.path.join(os.path.dirname(image_path), "processed_" + os.path.basename(image_path))

        image.save(output_path)
        print(f"Imagen procesada guardada en: {output_path}")
        return output_path

    except Exception as e:
        print(f"Error procesando la imagen: {e}")
        return None
