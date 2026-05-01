# src/search/logger.py
# Simple logging system for the search engine.
# Writes timestamped events to a log file in the project root.

import logging
import os
from datetime import datetime


LOG_PATH = os.path.join(
    os.path.dirname(__file__), '..', '..', 'search_engine.log')


def setup_logger() -> logging.Logger:
    """
    Set up and return the application logger.
    Logs to both file and console.
    """
    logger = logging.getLogger("local_search")
    logger.setLevel(logging.DEBUG)

    if logger.handlers:
        return logger

    # File handler — writes everything to search_engine.log
    fh = logging.FileHandler(LOG_PATH, encoding="utf-8")
    fh.setLevel(logging.DEBUG)

    # Console handler — shows INFO and above in terminal
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)

    # Format: timestamp · level · message
    fmt = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    fh.setFormatter(fmt)
    ch.setFormatter(fmt)

    logger.addHandler(fh)
    logger.addHandler(ch)

    logger.info("=== Session started ===")
    return logger


# Global logger instance
log = setup_logger()