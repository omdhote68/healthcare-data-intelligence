"""Logging setup.

Logging writes messages to both the screen and a file in logs/.
This gives us an audit trail of what the pipeline did and any errors.
"""

import logging

from src.config import LOG_DIR


def get_logger(name: str = "healthcare_pipeline") -> logging.Logger:
    """Return a configured logger. Safe to call many times."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(name)s | %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    try:
        LOG_DIR.mkdir(exist_ok=True)
        file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError:
        # Read-only hosting: keep going with console logging only.
        logger.warning("Could not create log file; using console logging only.")

    return logger
