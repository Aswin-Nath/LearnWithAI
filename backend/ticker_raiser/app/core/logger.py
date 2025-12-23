"""
Centralized logging system for Ticket Raiser
"""

import logging
import logging.handlers
import os
from datetime import datetime
from typing import Optional


class Logger:
    """Centralized logger for the application"""
    
    _instance = None
    _loggers = {}
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Initialize logging configuration"""
        # Create logs directory
        logs_dir = os.path.join(os.path.dirname(__file__), "..", "..", "logs")
        os.makedirs(logs_dir, exist_ok=True)
        
        # Configure root logger
        self.base_logger = logging.getLogger("ticket_raiser")
        self.base_logger.setLevel(logging.DEBUG)
        
        # Remove existing handlers
        self.base_logger.handlers.clear()
        
        # Format
        formatter = logging.Formatter(
            '[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # File handler - all logs
        file_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, "app.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        self.base_logger.addHandler(file_handler)
        
        # File handler - errors only
        error_handler = logging.handlers.RotatingFileHandler(
            os.path.join(logs_dir, "error.log"),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(formatter)
        self.base_logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_handler.setFormatter(formatter)
        self.base_logger.addHandler(console_handler)
    
    @staticmethod
    def get_logger(name: str) -> logging.Logger:
        """Get or create a logger for a module"""
        logger = logging.getLogger(f"ticket_raiser.{name}")
        logger.setLevel(logging.DEBUG)
        return logger


# Convenience functions
def get_logger(name: str) -> logging.Logger:
    """Get logger instance for a module"""
    return Logger.get_logger(name)


# Example usage in modules:
# from app.core.logger import get_logger
# logger = get_logger(__name__)
# logger.info("Message")
