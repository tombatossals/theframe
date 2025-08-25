"""Configuration management for TheFrame application."""

import logging
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field, validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from ..core.exceptions import ConfigurationError


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_prefix="THEFRAME_",
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # TV Configuration
    tv_ip: Optional[str] = Field(None, description="Samsung TV IP address")
    tv_token: Optional[str] = Field(None, description="Samsung TV authentication token")

    # File Paths
    artworks_json: Optional[str] = Field(None, description="Path to paintings JSON file")
    images_dir: Optional[str] = Field(None, description="Directory containing images")

    # URLs
    base_url: Optional[str] = Field(None, description="Base URL for images")
    source_json: Optional[str] = Field(None, description="Source JSON URL")

    # Processing
    batch_size: int = Field(5, description="Batch size for processing")
    max_retries: int = Field(3, description="Maximum retries for operations")

    # AI API keys
    ai_api_key: Optional[str] = Field(None, description="AI API KEY to use")
    ai_base_url: Optional[str] = Field(None, description="AI API base URL")

    # Logging
    log_level: str = Field("INFO", description="Logging level")
    log_format: str = Field("%(message)s", description="Logging format")

    @validator("tv_ip")
    def validate_tv_ip(cls, v: Optional[str]) -> Optional[str]:
        """Validate TV IP address format."""
        if v and not cls._is_valid_ip(v):
            raise ValueError("Invalid IP address format")
        return v

    @validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        """Validate logging level."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        if v.upper() not in valid_levels:
            raise ValueError(f"Invalid log level. Must be one of: {valid_levels}")
        return v.upper()

    @staticmethod
    def _is_valid_ip(ip: str) -> bool:
        """Basic IP address validation."""
        try:
            parts = ip.split(".")
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except (ValueError, AttributeError):
            return False

    def validate_for_upload(self) -> None:
        """Validate settings required for upload command."""
        if not self.tv_ip:
            raise ConfigurationError(
                "TV IP address is required for upload",
                "Set THEFRAME_TV_IP environment variable or use --ip"
            )
        if not self.tv_token:
            raise ConfigurationError(
                "TV token is required for upload",
                "Set THEFRAME_TV_TOKEN environment variable or use --token"
            )
        if not self.artworks_json:
            raise ConfigurationError(
                "Artworks JSON path is required for upload",
                "Set THEFRAME_ARTWORKS_JSON environment variable or use --artworks-json"
            )

    def validate_for_generate(self) -> None:
        """Validate settings required for generate command."""
        if not self.images_dir:
            raise ConfigurationError(
                "Images directory is required for generate",
                "Set THEFRAME_IMAGES_DIR environment variable or use --images-dir"
            )
        if not self.base_url:
            raise ConfigurationError(
                "Base URL is required for generate",
                "Set THEFRAME_BASE_URL environment variable or use --base-url"
            )
        if not self.artworks_json:
            raise ConfigurationError(
                "Artworks JSON path is required for generate",
                "Set THEFRAME_ARTWORKS_JSON environment variable or use --artworks-json"
            )

    def validate_for_update(self) -> None:
        """Validate settings required for update command."""
        if not self.images_dir:
            raise ConfigurationError(
                "Images directory is required for generate",
                "Set THEFRAME_IMAGES_DIR environment variable or use --images-dir"
            )
        if not self.base_url:
            raise ConfigurationError(
                "Base URL is required for generate",
                "Set THEFRAME_BASE_URL environment variable or use --base-url"
            )
        if not self.artworks_json:
            raise ConfigurationError(
                "Artworks JSON path is required for generate",
                "Set THEFRAME_ARTWORKS_JSON environment variable or use --artworks-json"
            )

    def validate_for_populate(self) -> None:
        """Validate settings required for populate command."""
        if not self.artworks_json:
            raise ConfigurationError(
                "Artworks JSON path is required for populate",
                "Set THEFRAME_ARTWORKS_JSON environment variable or use --artworks-json"
            )
        if not self.base_url:
            raise ConfigurationError(
                "Base URL is required for populate",
                "Set THEFRAME_BASE_URL environment variable or use --base-url"
            )


def setup_logging(settings: Settings) -> None:
    """Configure structured logging."""
    from .logging import setup_structlog
    setup_structlog(settings.log_level)


def load_settings() -> Settings:
    """Load and return application settings."""
    # Load environment variables from .env file
    load_dotenv()

    try:
        return Settings()
    except Exception as e:
        raise ConfigurationError(f"Failed to load configuration: {e}")


# Global settings instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get the global settings instance."""
    global _settings
    if _settings is None:
        _settings = load_settings()
    return _settings


def reset_settings() -> None:
    """Reset the global settings instance (useful for testing)."""
    global _settings
    _settings = None
