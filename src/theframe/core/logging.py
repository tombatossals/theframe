"""Structured logging configuration for TheFrame."""

import logging
from typing import Any, Dict

import structlog
from rich.console import Console
from rich.logging import RichHandler


def setup_structlog(log_level: str = "INFO") -> None:
    """Configure structlog with clean console output."""
    # Get numeric log level
    numeric_level = getattr(logging, log_level.upper())
    
    # Configure stdlib logging with simple formatting
    logging.basicConfig(
        level=numeric_level,
        format="%(message)s",
        handlers=[logging.StreamHandler()],
        force=True
    )
    
    # Configure structlog processors
    processors = [
        # Add context variables
        structlog.contextvars.merge_contextvars,
        
        # Add log level
        structlog.processors.add_log_level,
        
        # Add timestamp
        structlog.processors.TimeStamper(fmt="iso"),
        
        # Add caller info in debug mode
        structlog.processors.CallsiteParameterAdder(
            parameters=[
                structlog.processors.CallsiteParameter.FILENAME,
                structlog.processors.CallsiteParameter.FUNC_NAME,
                structlog.processors.CallsiteParameter.LINENO,
            ]
        ) if log_level.upper() == "DEBUG" else _noop_processor,
        
        # Clean console renderer with colors for better readability
        structlog.dev.ConsoleRenderer(colors=True)
    ]
    
    # Configure structlog
    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(numeric_level),
        logger_factory=structlog.stdlib.LoggerFactory(),
        context_class=dict,
        cache_logger_on_first_use=True,
    )


def _noop_processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """No-op processor that returns event_dict unchanged."""
    return event_dict


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a structlog logger for the given name."""
    return structlog.get_logger(name)