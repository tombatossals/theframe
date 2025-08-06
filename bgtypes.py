from typing import TypedDict


class BgMetadata(TypedDict):
    autor: str
    titulo: str
    genero: str
    siglo: str
    ur: str

class Background(TypedDict):
    metadata: BgMetadata
    binary: bytes
