import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class StructuredFormatter(logging.Formatter):
    """Custom logging formatter that supports structured formats.
    
    Outputs raw JSON lines in production/Docker, and beautifully colored ANSI
    logs in development/terminal, with zero external dependencies.
    """

    def __init__(self, json_format: bool = False):
        super().__init__()
        self.json_format = json_format

    def format(self, record: logging.LogRecord) -> str:
        # Standard structural fields
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "module": record.module,
            "line": record.lineno,
        }

        # Add structured context from the 'extra' dict if provided
        if hasattr(record, "extra") and isinstance(record.extra, dict):  # type: ignore
            log_data.update(record.extra)  # type: ignore

        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        if self.json_format:
            return json.dumps(log_data)
        else:
            # Color and styling definitions for CLI
            color_code = ""
            reset_code = "\033[0m"
            bold_code = "\033[1m"
            
            # ANSI Colors
            if record.levelno >= logging.CRITICAL:
                color_code = "\033[41m\033[37m"  # White on Red bg
            elif record.levelno >= logging.ERROR:
                color_code = "\033[31m"  # Red
            elif record.levelno >= logging.WARNING:
                color_code = "\033[33m"  # Yellow
            elif record.levelno >= logging.INFO:
                color_code = "\033[32m"  # Green
            elif record.levelno >= logging.DEBUG:
                color_code = "\033[36m"  # Cyan

            time_str = datetime.fromtimestamp(record.created).strftime("%Y-%m-%d %H:%M:%S")
            extra_str = ""
            
            # Print extra fields if present in human format
            if hasattr(record, "extra") and isinstance(record.extra, dict):  # type: ignore
                extra_kv = [f"{k}={v}" for k, v in record.extra.items()]  # type: ignore
                if extra_kv:
                    extra_str = f" \033[90m({', '.join(extra_kv)})\033[0m"

            return f"\033[90m{time_str}\033[0m {color_code}{bold_code}[{record.levelname:8}]{reset_code} \033[35m[{record.name}]\033[0m {record.getMessage()}{extra_str}"

def setup_logger(name: str = "sdai", level: Optional[str] = None) -> logging.Logger:
    """Configures and returns the unified application logger."""
    logger = logging.getLogger(name)
    
    # Resolve log level
    env_level = level or os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, env_level, logging.INFO)
    logger.setLevel(log_level)
    
    # Avoid duplicate logs if propagation is enabled
    logger.propagate = False

    # Clear pre-existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()

    # Determine format (JSON in Docker/production, Console in dev)
    env_format = os.getenv("LOG_FORMAT", "console").lower()
    json_format = (env_format == "json")

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(StructuredFormatter(json_format=json_format))
    logger.addHandler(handler)
    
    return logger

# Singleton Logger for the entire SDAI application
logger = setup_logger("sdai")
