from typing import Optional, TypedDict


class BgMetadata(TypedDict):
    """Metadata for background images."""

    author: str
    title: str
    style: str
    year: str
    century: str
    location: str
    wikipedia_url: str

class Background(TypedDict):
    """Background image with metadata and binary data."""

    metadata: BgMetadata
    binary: bytes
    number: Optional[int]
    filename: Optional[str]
    bg_url: Optional[str]
