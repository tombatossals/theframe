#!/usr/bin/env python

from PIL import Image, ImageDraw, ImageFont
import os
import sys

# Ruta de la imagen
image_path = sys.argv[1]

# Abrir la imagen
image = Image.open(image_path)

# Crear un objeto de dibujo
draw = ImageDraw.Draw(image)

# Obtener el nombre del archivo sin la ruta
file_name = os.path.basename(image_path).replace(".jpg", "")

# Configurar la fuente (asegúrate de que la fuente exista en tu sistema)
# Cambia la ruta según tu sistema
font_path = "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf"
font_size = 96
font = ImageFont.truetype(font_path, font_size)

# Obtener el tamaño de la imagen
image_width, image_height = image.size

# Calcular las dimensiones del texto usando textbbox
text_bbox = draw.textbbox((0, 0), file_name, font=font)
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
draw.text((text_x, text_y), file_name, font=font, fill="white")

# Guardar la nueva imagen
output_path = "/home/dave/dev/theframe/done.jpg"
image.save(output_path)
