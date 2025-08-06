import json
import os


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
                url = f"{base_url}/{ruta_relativa.replace(os.sep, '/').replace(' ', '%20')}"

                result.append({
                    "file_path": ruta_absoluta,
                    "url": url,
                    "level1": niveles[0] if len(niveles) > 0 else None,
                    "level2": niveles[1] if len(niveles) > 1 else None,
                    "level3": niveles[2] if len(niveles) > 2 else None
                })
    return result
