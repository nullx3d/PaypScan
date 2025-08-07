#!/usr/bin/env python3
"""
Log Manager - Categorized logging system
"""

import logging
import logging.handlers
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

class LogManager:
    """Categorized log management"""
    
    def __init__(self):
        self.setup_logging()
    
    def setup_logging(self):
        """Setup log files and formatters"""
        # Create log directory (use absolute path)
        self.log_dir = Path(__file__).parent.parent.parent / "logs"
        self.log_dir.mkdir(exist_ok=True)
        
        # Setup formatters
        detailed_formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Webhook events logger
        self._setup_webhook_logger(detailed_formatter)
        
        # Security alerts logger
        self._setup_security_logger(detailed_formatter)
        
        # Database operations logger
        self._setup_database_logger(detailed_formatter)
        
        # Errors logger
        self._setup_error_logger(detailed_formatter)
        
        # Audit logger
        self._setup_audit_logger(detailed_formatter)
        
        print("✅ Logging system started")
    
    def _setup_webhook_logger(self, formatter):
        """Setup webhook events logger"""
        webhook_logger = logging.getLogger('webhook_events')
        webhook_logger.setLevel(logging.INFO)
        
        # Rotating file handler (50MB max, 10 backup)
        webhook_handler = logging.handlers.RotatingFileHandler(
            str(self.log_dir / 'webhook_events.log'),
            maxBytes=50*1024*1024,  # 50MB
            backupCount=10
        )
        webhook_handler.setFormatter(formatter)
        webhook_logger.addHandler(webhook_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        webhook_logger.addHandler(console_handler)
    
    def _setup_security_logger(self, formatter):
        """Setup security alerts logger"""
        security_logger = logging.getLogger('security_alerts')
        security_logger.setLevel(logging.WARNING)
        
        # Rotating file handler (20MB max, 5 backup)
        security_handler = logging.handlers.RotatingFileHandler(
            str(self.log_dir / 'security_alerts.log'),
            maxBytes=20*1024*1024,  # 20MB
            backupCount=5
        )
        security_handler.setFormatter(formatter)
        security_logger.addHandler(security_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        security_logger.addHandler(console_handler)
    
    def _setup_database_logger(self, formatter):
        """Setup database operations logger"""
        db_logger = logging.getLogger('database_operations')
        db_logger.setLevel(logging.INFO)
        
        # Rotating file handler (10MB max, 3 backup)
        db_handler = logging.handlers.RotatingFileHandler(
            str(self.log_dir / 'database_operations.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        db_handler.setFormatter(formatter)
        db_logger.addHandler(db_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        db_logger.addHandler(console_handler)
    
    def _setup_error_logger(self, formatter):
        """Setup errors logger"""
        error_logger = logging.getLogger('errors')
        error_logger.setLevel(logging.ERROR)
        
        # Rotating file handler (5MB max, 2 backup)
        error_handler = logging.handlers.RotatingFileHandler(
            str(self.log_dir / 'errors.log'),
            maxBytes=5*1024*1024,  # 5MB
            backupCount=2
        )
        error_handler.setFormatter(formatter)
        error_logger.addHandler(error_handler)
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        error_logger.addHandler(console_handler)
    
    def _setup_audit_logger(self, formatter):
        """Setup audit logger"""
        audit_logger = logging.getLogger('audit')
        audit_logger.setLevel(logging.INFO)
        
        # Rotating file handler (10MB max, 3 backup)
        audit_handler = logging.handlers.RotatingFileHandler(
            str(self.log_dir / 'audit.log'),
            maxBytes=10*1024*1024,  # 10MB
            backupCount=3
        )
        audit_handler.setFormatter(formatter)
        audit_logger.addHandler(audit_handler)
    
    def log_webhook(self, level: str, message: str, **kwargs):
        """Log webhook events"""
        logger = logging.getLogger('webhook_events')
        full_message = f"{message} | {kwargs}"
        getattr(logger, level.lower())(full_message)
    
    def log_security(self, level: str, message: str, **kwargs):
        """Log security alerts"""
        logger = logging.getLogger('security_alerts')
        full_message = f"{message} | {kwargs}"
        getattr(logger, level.lower())(full_message)
    
    def log_database(self, level: str, message: str, **kwargs):
        """Log database operations"""
        logger = logging.getLogger('database_operations')
        full_message = f"{message} | {kwargs}"
        getattr(logger, level.lower())(full_message)
    
    def log_error(self, message: str, **kwargs):
        """Log errors"""
        logger = logging.getLogger('errors')
        full_message = f"{message} | {kwargs}"
        logger.error(full_message)
    
    def log_audit(self, message: str, **kwargs):
        """Log audit trail"""
        logger = logging.getLogger('audit')
        full_message = f"{message} | {kwargs}"
        logger.info(full_message)
    
    def get_log_info(self) -> Dict[str, Any]:
        """Return information about log files"""
        log_info = {}
        
        for log_file in self.log_dir.glob("*.log"):
            size_mb = log_file.stat().st_size / (1024*1024)
            log_info[log_file.name] = {
                'size_mb': round(size_mb, 2),
                'last_modified': datetime.fromtimestamp(log_file.stat().st_mtime).isoformat()
            }
        
        return log_info

# Global log manager instance
log_manager = LogManager() 