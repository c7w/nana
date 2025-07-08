"""
This module sets up a colored logger for the application.
"""
import logging
import colorlog

def setup_logging():
    """
    Configures the root logger for colored output with a specific format.
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(colorlog.ColoredFormatter(
        '%(log_color)s[%(levelname)-8s] [%(filename)s:%(lineno)d] %(message)s',
        log_colors={
            'DEBUG':    'cyan',
            'INFO':     'green',
            'WARNING':  'yellow',
            'ERROR':    'red',
            'CRITICAL': 'red,bg_white',
        },
        reset=True,
        style='%'
    ))

    # Get the root logger
    root_logger = logging.getLogger()
    
    # Check if the logger already has handlers to avoid adding them multiple times
    if not root_logger.handlers:
        root_logger.addHandler(handler)
        root_logger.setLevel(logging.INFO) 