"""Exception classes for TheFrame application."""

from typing import Optional


class TheFrameError(Exception):
    """Base exception for TheFrame application."""
    
    def __init__(self, message: str, details: Optional[str] = None) -> None:
        self.message = message
        self.details = details
        super().__init__(self.message)


class ConfigurationError(TheFrameError):
    """Raised when configuration is invalid or missing."""
    pass


class TVConnectionError(TheFrameError):
    """Raised when TV connection fails."""
    pass


class ImageProcessingError(TheFrameError):
    """Raised when image processing fails."""
    pass


class MetadataError(TheFrameError):
    """Raised when metadata processing fails."""
    pass


class FileOperationError(TheFrameError):
    """Raised when file operations fail."""
    pass