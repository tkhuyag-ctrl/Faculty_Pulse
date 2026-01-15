"""
Centralized Logging Configuration for Faculty Pulse
Provides consistent logging setup across all modules
"""
import logging
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Fix encoding for Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Create logs directory if it doesn't exist
LOGS_DIR = Path("./logs")
LOGS_DIR.mkdir(exist_ok=True)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output"""

    # ANSI color codes
    COLORS = {
        'DEBUG': '\033[36m',      # Cyan
        'INFO': '\033[32m',       # Green
        'WARNING': '\033[33m',    # Yellow
        'ERROR': '\033[31m',      # Red
        'CRITICAL': '\033[35m',   # Magenta
        'RESET': '\033[0m'        # Reset
    }

    def format(self, record):
        # Add color to levelname
        if record.levelname in self.COLORS:
            record.levelname = (
                f"{self.COLORS[record.levelname]}"
                f"{record.levelname}"
                f"{self.COLORS['RESET']}"
            )
        return super().format(record)


def setup_logger(
    name: str,
    log_file: Optional[str] = None,
    level: int = logging.INFO,
    console: bool = True,
    colored: bool = True
) -> logging.Logger:
    """
    Setup a logger with file and console handlers

    Args:
        name: Logger name (usually __name__)
        log_file: Optional log file name (will be placed in ./logs/)
        level: Logging level (default: INFO)
        console: Whether to output to console (default: True)
        colored: Whether to use colored console output (default: True)

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Clear any existing handlers
    logger.handlers.clear()

    # Create formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    simple_formatter = logging.Formatter(
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    if console:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)

        if colored and sys.platform != "win32":
            # Use colored formatter on non-Windows or if terminal supports colors
            console_formatter = ColoredFormatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%H:%M:%S'
            )
            console_handler.setFormatter(console_formatter)
        else:
            console_handler.setFormatter(simple_formatter)

        logger.addHandler(console_handler)

    # File handler
    if log_file:
        log_path = LOGS_DIR / log_file
        file_handler = logging.FileHandler(log_path, encoding='utf-8')
        file_handler.setLevel(level)
        file_handler.setFormatter(detailed_formatter)
        logger.addHandler(file_handler)

    return logger


def log_function_call(logger: logging.Logger, func_name: str, **kwargs):
    """
    Log a function call with its parameters

    Args:
        logger: Logger instance
        func_name: Function name
        **kwargs: Function parameters to log
    """
    params = ", ".join(f"{k}={v}" for k, v in kwargs.items())
    logger.info(f"CALL: {func_name}({params})")


def log_result(logger: logging.Logger, func_name: str, result: any, duration: float = None):
    """
    Log a function result

    Args:
        logger: Logger instance
        func_name: Function name
        result: Result to log
        duration: Optional duration in seconds
    """
    duration_str = f" ({duration:.2f}s)" if duration else ""
    logger.info(f"RESULT: {func_name}{duration_str} -> {result}")


def log_error(logger: logging.Logger, func_name: str, error: Exception):
    """
    Log an error with traceback

    Args:
        logger: Logger instance
        func_name: Function name where error occurred
        error: Exception that was raised
    """
    logger.error(f"ERROR in {func_name}: {type(error).__name__}: {str(error)}", exc_info=True)


def log_progress(logger: logging.Logger, current: int, total: int, item_name: str = "items"):
    """
    Log progress of a batch operation

    Args:
        logger: Logger instance
        current: Current item number
        total: Total number of items
        item_name: Name of items being processed
    """
    percentage = (current / total * 100) if total > 0 else 0
    logger.info(f"Progress: {current}/{total} {item_name} ({percentage:.1f}%)")


# Quick setup functions for common use cases

def setup_crawler_logger(script_name: str) -> logging.Logger:
    """Setup logger for crawler scripts"""
    return setup_logger(
        name=script_name,
        log_file=f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        level=logging.INFO,
        console=True,
        colored=True
    )


def setup_extractor_logger(script_name: str) -> logging.Logger:
    """Setup logger for data extraction scripts"""
    return setup_logger(
        name=script_name,
        log_file=f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        level=logging.INFO,
        console=True,
        colored=True
    )


def setup_integration_logger(script_name: str) -> logging.Logger:
    """Setup logger for integration scripts"""
    return setup_logger(
        name=script_name,
        log_file=f"{script_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log",
        level=logging.INFO,
        console=True,
        colored=True
    )


if __name__ == "__main__":
    # Test the logging setup
    print("Testing logging configuration...\n")

    logger = setup_logger("test_logger", "test.log")

    logger.debug("This is a debug message")
    logger.info("This is an info message")
    logger.warning("This is a warning message")
    logger.error("This is an error message")
    logger.critical("This is a critical message")

    log_function_call(logger, "test_function", param1="value1", param2=42)
    log_result(logger, "test_function", "success", duration=1.23)
    log_progress(logger, 5, 10)

    print(f"\nLog file created at: {LOGS_DIR / 'test.log'}")
