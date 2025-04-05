#!/usr/bin/env python3
"""
Database configuration module for the AMR predictor.

This module provides centralized configuration settings for database paths,
ensuring consistent access across the application. Both AMR and Bakta
services use the same unified SQLite database file.
"""

import os
from pathlib import Path
from typing import Union, Optional

# Base project directory
PROJECT_ROOT = Path(__file__).parent.parent.parent.resolve()

# Single database directory and file for all services
DB_DIR = PROJECT_ROOT / "data" / "db"
DB_FILE = DB_DIR / "predictor.db"

def get_database_path(custom_path: Optional[Union[str, Path]] = None) -> Path:
    """
    Get the appropriate database path based on the optional custom path.
    If no custom path is provided, returns the default path in the project directory.
    
    Args:
        custom_path: Optional custom database path

    Returns:
        Path object pointing to the database file
    """
    if custom_path:
        db_path = Path(custom_path)
    else:
        # Use default project-based path
        db_path = DB_FILE
    
    # Ensure parent directory exists
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    return db_path
