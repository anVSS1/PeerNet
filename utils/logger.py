import logging
import sys
from datetime import datetime
from pathlib import Path

def setup_logging(log_level: str = 'INFO', log_file: str = None):
    """
    Set up logging configuration for the application.
    """
    # Create logs directory if it doesn't exist
    if log_file:
        # Validate log file path to prevent path traversal
        log_path = Path(log_file).resolve()
        if not str(log_path).startswith(str(Path.cwd())):
            raise ValueError("Log file path must be within current directory")
        log_dir = log_path.parent
        log_dir.mkdir(parents=True, exist_ok=True)

    # Configure logging
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    date_format = '%Y-%m-%d %H:%M:%S'

    # Set up formatter
    formatter = logging.Formatter(log_format, date_format)

    # Set up console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Set up file handler if log_file is specified
    handlers = [console_handler]
    if log_file:
        try:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)
        except Exception as e:
            print("Warning: Could not create log file handler: %s" % str(e))

    # Configure root logger
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        handlers=handlers
    )

    # Set specific loggers for external libraries to reduce noise
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('mongoengine').setLevel(logging.WARNING)
    logging.getLogger('transformers').setLevel(logging.WARNING)
    logging.getLogger('torch').setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info("Logging initialized with level %s", log_level)

def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a specific module.
    """
    return logging.getLogger(name)
