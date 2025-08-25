import glob
import json
import os

import requests
import slugify
from dotenv import load_dotenv

load_dotenv()

url = os.getenv("SONAR_BASE_URL")
headers = {
    "Authorization": f"Bearer {os.getenv('SONAR_API_KEY')}",
    "Content-Type": "application/json"
}

def get_artwork_info(author_title: str) -> dict | None:
    """
    Dado un pintor y el nombre (aproximado) de una obra,
    devuelve información estructurada en formato JSON.
    """

    payload = {
        "model": "sonar-pro",
        "messages": [
            {
                "role": "user",
                "content": f"""
    Dado el siguiente pintor y una obra (puede tener errores ortográficos),
    devuelve un JSON con la siguiente estructura:

    {{
        "author": <AUTHOR>,
        "title": <TITLE>,
        "style": <STYLE>,
        "year": <YEAR>,
        "century": <CENTURY en números romanos>,
        "location": <LOCATION>,
        "wikipedia_url": <WIKIPEDIA_URL>,
        "i18n": {{
            "es": {{
                "author": <AUTHOR_ES>,
                "title": <TITLE_ES>,
                "style": <STYLE_ES>,
                "location": <LOCATION_ES>
            }}
        }}
    }}

    Pintor y título aproximado: "{author_title}"

    IMPORTANTE:
    - Corrige el título si está mal escrito o incompleto, devolviendo el más parecido posible.
    - El siglo debe ir en números romanos (ej. XIX, XVII).
    - Responde ÚNICAMENTE con el JSON válido, sin explicaciones adicionales.
    - Evita incluir código Markdown indicando que es JSON en la respuesta.
    """
            }
        ]
    }

    response = requests.post(url, headers=headers, json=payload)

    try:
        r = response.json()
    except Exception:
        print("⚠️ La API no devolvió JSON válido. Respuesta cruda:")
        print(response.text[:500])
        return None

    # dump para depuración
    with open("dump.json", 'w', encoding='utf-8') as f:
        json.dump(r, f, ensure_ascii=False, indent=2)

    content = r.get("choices", [{}])[0].get("message", {}).get("content")
    if not content:
        print("⚠️ No se encontró contenido en la respuesta:", r)
        return None

    try:
        return json.loads(content)
    except json.JSONDecodeError:
        print("⚠️ El modelo devolvió algo que no es JSON válido:")
        print(content)
        return None


if __name__ == "__main__":
    with open(os.getenv("THEFRAME_POPULATED_JSON"), "r", encoding='utf-8') as paintings:
        paintings_data = json.load(paintings)

        for painting in [p for p in paintings_data.values()
                         if not glob.glob(os.path.join("json", str(p.get("number")).zfill(4) + "*"))][:10]:
            author_title = painting.get("author") + " - " + painting.get("title")
            number = painting.get("number")

            result = get_artwork_info(author_title)
            if not result:
                continue  # saltar si no hubo respuesta válida

            result["number"] = number

            filename = os.path.join(
                "./json",
                str(number).zfill(4) + "-" + slugify.slugify(author_title) + ".json"
            )

            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
                print(f"Guardado en {filename}")
