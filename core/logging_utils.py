"""
Core Logging Utilities.

This module provides standard logging configuration and helpers.
It replaces the custom print-based loggers with the Python standard library `logging` module.
"""

import logging
import sys
from colorama import Fore, Style, init

# Initialize colorama
init()

# Custom Formatter for colored output
class ColoredFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: Fore.CYAN,
        logging.INFO: Fore.GREEN,
        logging.WARNING: Fore.YELLOW,
        logging.ERROR: Fore.RED,
        logging.CRITICAL: Fore.RED + Style.BRIGHT,
    }

    def format(self, record):
        log_color = self.COLORS.get(record.levelno, "")
        reset = Style.RESET_ALL
        timestamp = self.formatTime(record, self.datefmt)
        
        # Format: [TIME] [LEVEL] Message
        formatted_msg = f"{Style.DIM}[{timestamp}]{reset} {log_color}[{record.levelname}]{reset} {record.getMessage()}"
        return formatted_msg

def setup_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Sets up a logger with a colored console handler.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Avoid adding multiple handlers if already setup
    if not logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(ColoredFormatter("%Y-%m-%d %H:%M:%S"))
        logger.addHandler(console_handler)
    
    return logger

# Global default logger
logger = setup_logger("agent_generator")
