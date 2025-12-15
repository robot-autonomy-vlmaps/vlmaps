import logging
import os
import sys
from logging import Handler, LogRecord
from logging.handlers import RotatingFileHandler
from typing import Iterable, Optional


def _resolve_level(default: str = "INFO") -> int:
    level_str = os.getenv("VLMAPS_LOG_LEVEL", default).upper()
    return getattr(logging, level_str, logging.getLevelName(level_str)) or logging.INFO


class _ColorFormatter(logging.Formatter):
    BASE_FMT = "%(levelname)-8s [%(name)s] [%(filename)s:%(lineno)d]\n\t%(message)s"
    COLORS = {
        logging.DEBUG: "\033[36m",  # cyan
        logging.INFO: "\033[32m",  # green
        logging.WARNING: "\033[33m",  # yellow
        logging.ERROR: "\033[31m",  # red
        logging.CRITICAL: "\033[35m",  # magenta
    }
    RESET = "\033[0m"

    def __init__(self, use_color: bool) -> None:
        super().__init__(self.BASE_FMT)
        self.use_color = use_color

    def format(self, record: LogRecord) -> str:
        original_levelname = record.levelname
        original_name = record.name
        original_filename = record.filename
        if self.use_color:
            color = self.COLORS.get(record.levelno, "")
            record.levelname = f"{color}{record.levelname}{self.RESET}"
            record.name = f"{color}{record.name}{self.RESET}"
            record.filename = f"{color}{record.filename}{self.RESET}"
        formatted = super().format(record)
        record.levelname = original_levelname
        record.name = original_name
        record.filename = original_filename
        return formatted


def setup_logging(
    level: str = "INFO",
    log_file: Optional[str] = None,
    max_bytes: int = 5_000_000,
    backup_count: int = 3,
    handlers: Optional[Iterable[logging.Handler]] = None,
) -> None:
    """
    Configure root logging once with console output and optional rotation.
    Idempotent: returns early if handlers already exist.
    """
    if logging.getLogger().handlers:
        return

    log_level = _resolve_level(level)
    log_handlers: list[logging.Handler] = list(handlers) if handlers else []
    if not log_handlers:
        log_handlers.append(logging.StreamHandler())
        if log_file:
            log_handlers.append(
                RotatingFileHandler(log_file, maxBytes=max_bytes, backupCount=backup_count)
            )

    logging.basicConfig(level=log_level, handlers=log_handlers)

    for handler in log_handlers:
        is_tty = hasattr(handler, "stream") and handler.stream in (sys.stdout, sys.stderr) and handler.stream.isatty()
        if isinstance(handler, RotatingFileHandler):
            handler.setFormatter(logging.Formatter(_ColorFormatter.BASE_FMT))
        else:
            handler.setFormatter(_ColorFormatter(use_color=is_tty))


