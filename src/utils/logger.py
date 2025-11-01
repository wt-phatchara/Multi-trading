"""Logging configuration for the trading agent."""
import logging
import coloredlogs
from datetime import datetime
from pathlib import Path


def setup_logger(name: str, log_level: str = 'INFO') -> logging.Logger:
    """
    Setup and configure logger with colored output and file logging.

    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(getattr(logging, log_level.upper()))

    # Create logs directory if it doesn't exist
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)

    # File handler
    log_file = log_dir / f"trading_{datetime.now().strftime('%Y%m%d')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)

    # Colored console output
    coloredlogs.install(
        level=log_level.upper(),
        logger=logger,
        fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        level_styles={
            'debug': {'color': 'cyan'},
            'info': {'color': 'green'},
            'warning': {'color': 'yellow'},
            'error': {'color': 'red'},
            'critical': {'color': 'red', 'bold': True},
        }
    )

    return logger
