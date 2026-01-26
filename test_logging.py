#!/usr/bin/env python3

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_logging'))

try:
    import importlib.util
    spec = importlib.util.spec_from_file_location("logger", os.path.join(os.path.dirname(os.path.abspath(__file__)), 'custom_logging', 'logger.py'))
    logger_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(logger_module)
    AppLogger = logger_module.AppLogger
except Exception as e:
    print(f"Failed to import AppLogger: {e}")
    AppLogger = None

def cleanup_directories():
    import shutil
    # Initialize logger
    if AppLogger:
        app_logger = AppLogger()
        logger = app_logger.logger
        logger.info("Test logging started - using AppLogger")
    else:
        # Fallback to basic file logging
        import logging as python_logging
        os.makedirs('logs', exist_ok=True)
        python_logging.basicConfig(
            level=python_logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                python_logging.FileHandler('logs/info.log'),
                python_logging.StreamHandler()
            ]
        )
        logger = python_logging.getLogger(__name__)
        logger.info("Test logging started - using basic logging")
    
    try:
        if os.path.exists("app-downloads"):
            logger.debug("Starting deletion of app-downloads directory")
            shutil.rmtree("app-downloads")
            logger.debug("Successfully deleted app-downloads directory")
        else:
            logger.debug("app-downloads directory does not exist, skipping deletion")
    except Exception as e:
        logger.error(f"Failed to delete app-downloads directory: {e}")
    
    # Test logging some more messages
    logger.info("Test logging complete")
    logger.warning("This is a warning message")
    logger.error("This is an error message")

if __name__ == "__main__":
    cleanup_directories()