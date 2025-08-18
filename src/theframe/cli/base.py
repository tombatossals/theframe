"""Base command interface for TheFrame CLI."""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Dict

from ..core.config import Settings
from ..core.exceptions import TheFrameError
from ..core.logging import get_logger


class BaseCommand(ABC):
    """Base class for all CLI commands."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.logger = get_logger(self.__class__.__name__)
    
    @abstractmethod
    def validate_settings(self) -> None:
        """Validate settings required for this command."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs: Any) -> None:
        """Execute the command."""
        pass
    
    def run(self, **kwargs: Any) -> None:
        """Run the command with proper error handling."""
        try:
            self.validate_settings()
            asyncio.run(self.execute(**kwargs))
        except TheFrameError as e:
            self.logger.error("Command failed", error=e.message, details=e.details)
            raise
        except Exception as e:
            self.logger.error("Unexpected error", error=str(e), exc_info=True)
            raise