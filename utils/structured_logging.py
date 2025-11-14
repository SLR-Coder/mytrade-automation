# utils/structured_logging.py
# -*- coding: utf-8 -*-
"""
Structured logging configuration
"""

import os
import sys
import logging
import json
from datetime import datetime
from functools import wraps
import time

def setup_logging(
    environment: str = "development",
    log_level: str = "INFO",
    enable_json: bool = False,
    enable_cloud_logging: bool = False
):
    """
    Setup structured logging

    Args:
        environment: Environment (development/production)
        log_level: Logging level
        enable_json: Enable JSON format
        enable_cloud_logging: Enable Google Cloud Logging
    """
    # Set log level
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers = []

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)

    if enable_json:
        # JSON formatter
        formatter = JsonFormatter()
    else:
        # Standard formatter
        if environment == "development":
            format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        else:
            format_string = "%(levelname)s:%(name)s:%(message)s"
        formatter = logging.Formatter(format_string)

    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add Google Cloud Logging if enabled
    if enable_cloud_logging and environment == "production":
        try:
            import google.cloud.logging
            cloud_client = google.cloud.logging.Client()
            cloud_handler = cloud_client.get_default_handler()
            root_logger.addHandler(cloud_handler)
            logging.info("Google Cloud Logging enabled")
        except Exception as e:
            logging.warning(f"Failed to setup Cloud Logging: {e}")

def get_logger(name: str) -> logging.Logger:
    """Get a logger instance"""
    return logging.getLogger(name)

class JsonFormatter(logging.Formatter):
    """JSON log formatter"""

    def format(self, record):
        log_obj = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }

        # Add exception info if present
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)

        # Add extra fields
        for key, value in record.__dict__.items():
            if key not in ["name", "msg", "args", "created", "filename", "funcName",
                          "levelname", "levelno", "lineno", "module", "msecs",
                          "pathname", "process", "processName", "relativeCreated",
                          "thread", "threadName", "exc_info", "exc_text", "getMessage"]:
                log_obj[key] = value

        return json.dumps(log_obj)

def log_async_execution_time(func):
    """Decorator to log async function execution time"""
    @wraps(func)
    async def wrapper(*args, **kwargs):
        start_time = time.time()
        logger = logging.getLogger(func.__module__)

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"{func.__name__} completed",
                extra={"execution_time": execution_time}
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"{func.__name__} failed",
                extra={"execution_time": execution_time, "error": str(e)}
            )
            raise

    return wrapper