"""
Logging configuration for the Binance Futures Trading Bot.
Sets up both file and console handlers with structured formatting.
"""

import logging
import logging.handlers
import os
from datetime import datetime


LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs")


def setup_logging(log_level: str = "INFO") -> logging.Logger:
    """
    Configure and return the root logger with file and console handlers.

    Args:
        log_level: Logging level string (DEBUG, INFO, WARNING, ERROR).

    Returns:
        Configured logger instance.
    """
    os.makedirs(LOG_DIR, exist_ok=True)

    log_filename = os.path.join(LOG_DIR, f"trading_bot_{datetime.now():%Y%m%d}.log")

    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    logger = logging.getLogger("trading_bot")
    logger.setLevel(logging.DEBUG)  # Capture everything; handlers filter

    if logger.handlers:
        return logger

    # ── File handler ── full detail to disk
    file_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_filename, maxBytes=5 * 1024 * 1024, backupCount=5, encoding="utf-8"
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)

    # ── Console handler ── clean output for the terminal
    console_fmt = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(message)s",
        datefmt="%H:%M:%S",
    )
    console_handler = logging.StreamHandler()
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(console_fmt)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    logger.info("Logging initialised → %s", log_filename)
    return logger


def get_logger(name: str) -> logging.Logger:
    """Return a child logger under the 'trading_bot' namespace."""
    return logging.getLogger(f"trading_bot.{name}")
