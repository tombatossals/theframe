"""Core domain models for TheFrame application."""

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union
from urllib.parse import urlparse

import requests
from pydantic import BaseModel, Field, validator
from slugify import slugify


class ArtworkTranslation(BaseModel):
    author: Optional[str] = None
    title: Optional[str] = None
    style: Optional[str] = None
    year: Optional[str] = None
    century: Optional[str] = None
    location: Optional[str] = None

class ArtworkMetadata(BaseModel):
    """Metadata for artwork pieces."""

    author: str = Field(..., description="Artist name")
    title: str = Field(..., description="Artwork title")
    style: str = Field(..., description="Art style/movement")
    year: str = Field(..., description="Creation year")
    century: str = Field(..., description="Century period")
    location: str = Field(..., description="Current location")
    wikipedia_url: Optional[str] = Field(None, description="Wikipedia URL")
    i18n: Optional[Dict[str, ArtworkTranslation]] = None

    @validator('year', pre=True)
    def validate_year(cls, v: Union[str, int]) -> str:
        """Convert year to string if needed."""
        return str(v)

    @validator('wikipedia_url')
    def validate_wikipedia_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not urlparse(v).scheme:
            return f"https://{v}"
        return v


class Artwork(BaseModel):
    """Complete artwork with metadata and file information."""

    number: Optional[int] = Field(None, description="Artwork number")
    metadata: ArtworkMetadata
    binary_data: Optional[bytes] = Field(None, description="Image binary data")

    class Config:
        arbitrary_types_allowed = True

    def bg_url_exists(self, base_url) -> bool:
        """Check if a BG_URL exists."""
        if self.bg_url is not None or base_url is None:
            return False

        url = f"{base_url}/{self.filename}"

        try:
            response = requests.head(url, allow_redirects=True, timeout=10)
            result: bool = response.status_code == 200
            return result
        except requests.RequestException as e:
            return False

    @property
    def filename(self) -> Optional[str]:
        """Get the image filename."""
        n = f"{str(self.number).zfill(4)} - {self.metadata.author} - {self.metadata.title}"
        return f"{slugify(n)}.jpg"

    @property
    def bg_url(self) -> Optional[str]:
        """Get the background URL."""
        return f"{os.getenv('THEFRAME_BASE_URL')}/{self.filename}"

    @property
    def display_name(self) -> str:
        """Human readable display name."""
        return f"{self.metadata.title} by {self.metadata.author}"

    @property
    def safe_filename(self) -> str:
        """Generate safe filename for the artwork."""
        if self.filename:
            return self.filename
        safe_title = "".join(c for c in self.metadata.title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_author = "".join(c for c in self.metadata.author if c.isalnum() or c in (' ', '-', '_')).strip()
        return f"{safe_author}_{safe_title}.jpg".replace(' ', '_')


class TVDevice(BaseModel):
    """Samsung TV device configuration."""

    ip: str = Field(..., description="TV IP address")
    token: str = Field(..., description="TV authentication token")
    name: Optional[str] = Field("Samsung Frame TV", description="Device name")

    @validator('ip')
    def validate_ip(cls, v: str) -> str:
        """Basic IP validation."""
        parts = v.split('.')
        if len(parts) != 4:
            raise ValueError('Invalid IP address format')
        try:
            for part in parts:
                if not 0 <= int(part) <= 255:
                    raise ValueError('Invalid IP address range')
        except ValueError:
            raise ValueError('Invalid IP address')
        return v


class ProcessingJob(BaseModel):
    """Background processing job for artwork generation."""

    id: str = Field(..., description="Unique job identifier")
    status: str = Field("pending", description="Job status")
    artworks: List[Artwork] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class ArtworkCollection(BaseModel):
    """Collection of artworks with metadata."""

    name: str = Field(..., description="Collection name")
    artworks: Dict[str, Artwork] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None

    class Config:
        arbitrary_types_allowed = True

    def add_artwork(self, artwork: Artwork) -> None:
        """Add artwork to collection."""
        key = f"{artwork.number}" if artwork.number else artwork.safe_filename
        self.artworks[key] = artwork
        self.updated_at = datetime.now()

    def get_random_artwork(self) -> Optional[Artwork]:
        """Get a random artwork from collection."""
        if not self.artworks:
            return None
        import random
        return random.choice(list(self.artworks.values()))

    def count(self) -> int:
        """Get number of artworks in collection."""
        return len(self.artworks)
