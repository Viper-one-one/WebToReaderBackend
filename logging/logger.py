import logging
import os
from logging.handlers import RotatingFileHandler
from datetime import datetime
import glob

class AppLogger:
    """Application Logger with rotating file handler."""

    def __init__(self, log_dir='logs', max_bytes=1_000_000, backup_count=5, max_age=10, max_lines=1000):
        self.log_dir = log_dir
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        self.max_bytes = max_bytes
        self.backup_count = backup_count
        self.max_age = max_age
        self.max_lines = max_lines

        log_file = os.path.join(log_dir, 'info.log')
        self.logger = logging.getLogger('AppLogger')
        self.logger.setLevel(logging.INFO)

        self.logger.handlers.clear()
        self._setup_handlers()
        self._cleanup_logs()
        
    def _setup_handlers(self):
        log_file = os.path.join(self.log_dir, 'info.log')
        file_handler = RotatingFileHandler(
            log_file, maxBytes=self.max_bytes, backupCount=self.backup_count, encoding='utf-8'
        )
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)
        console_formatter = logging.Formatter(
            '%(levelname)s - %(message)s'
        )
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)
        