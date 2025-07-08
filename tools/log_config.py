"""
This module sets up a colored logger for the application.
"""
import logging
import colorlog
from datetime import datetime
from pathlib import Path

def setup_logging():
    """
    Configures the root logger for colored console output and file-based error logging.
    """
    # --- Create Handlers ---
    console_handler = colorlog.StreamHandler()
    
    # Create logs directory if it doesn't exist
    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    
    # Generate a timestamped log file name
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    error_log_file = log_dir / f"error-{timestamp}.out"
    file_handler = logging.FileHandler(error_log_file, mode='w')

    # --- Set Log Levels ---
    console_handler.setLevel(logging.INFO)
    file_handler.setLevel(logging.ERROR)

    # --- Create Formatters ---
    console_formatter = colorlog.ColoredFormatter(
        '%(log_color)s[%(levelname)-8s] [%(filename)s:%(lineno)d]%(reset)s %(message)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        secondary_log_colors={
            'message': {
                'INFO':     'white',
                'WARNING':  'yellow',
                'ERROR':    'red',
                'CRITICAL': 'red',
            }
        },
        reset=True,
        style='%'
    )
    file_formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)-8s] [%(filename)s:%(lineno)d]\n%(message)s\n'
    )

    # --- Apply Formatters to Handlers ---
    console_handler.setFormatter(console_formatter)
    file_handler.setFormatter(file_formatter)

    # --- Add Handlers to Root Logger ---
    root_logger = logging.getLogger()
    
    # Check if handlers already exist to avoid duplication
    if not root_logger.handlers:
        root_logger.addHandler(console_handler)
        root_logger.addHandler(file_handler)
        root_logger.setLevel(logging.DEBUG) # Set root to lowest level to capture all messages 