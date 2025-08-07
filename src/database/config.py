"""
Database configuration for pipeline security analysis
"""

import os
from pathlib import Path

# Database file path
BASE_DIR = Path(__file__).parent.parent.parent
DATABASE_DIR = BASE_DIR / "data" / "database"
DATABASE_FILE = DATABASE_DIR / "pipeline_security.db"

# Ensure database directory exists
DATABASE_DIR.mkdir(parents=True, exist_ok=True)

# Database URL
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Database settings
DATABASE_CONFIG = {
    "echo": False,  # SQL queries logging
    "pool_pre_ping": True,
    "pool_recycle": 3600,
}

# Logging configuration
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
} 