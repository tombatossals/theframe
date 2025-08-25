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



def get_artwork_info(author_title: str) -> dict:
    """
    Dado un pintor y el nombre (aproximado) de una obra,
    devuelve información estructurada en formato JSON.
    """

    payload = {
    "model": "sonar-pro",
    "messages": [
        {"role": "user", "content": f"""
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
    """
        }
    ]}

    response = requests.post(url, headers=headers, json=payload)

    r = response.json()

    with open("test.json", 'w', encoding='utf-8') as f:
      json.dump(r.get("choices")[0].get("message").get("content"), f, ensure_ascii=False, indent=2)

    return r.get("choices")[0].get("message").get("content")

if __name__ == "__main__":
    # Ejemplo de uso
    #result = get_artwork_info("Vincent van Gogh - Noches estrelada")
    with open(os.getenv("THEFRAME_POPULATED_JSON"), "r", encoding='utf-8') as paintings:
        paintings_data = json.load(paintings)
        for painting in [p for p in paintings_data.values() if not glob.glob(os.path.join("./json", str(p.get("number")).zfill(4)))][:2]:
            author_title = painting.get("author") + " - " + painting.get("title")
            print(f"Buscando info para: {author_title}")
            r = get_artwork_info(author_title)
            result = json.loads(r)
            print(type(result))
            result["number"] = number

            with open(os.path.join("./json", str(number).zfill(4) + "-" + slugify.slugify(author_title) + ".json"), 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Guardado en ./json/{str(number).zfill(4)}-{slugify.slugify(author_title)}.json")

