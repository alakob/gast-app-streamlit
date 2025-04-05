#!/usr/bin/env python3
"""
Job lifecycle configuration management.

This module provides configuration for job retention, archiving, and cleanup.
"""
import os
import yaml
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logger = logging.getLogger("job-lifecycle-config")

# Default configuration
DEFAULT_CONFIG = {
    "retention_periods": {
        "Completed": 30,  # Days to keep completed jobs
        "Error": 14,      # Days to keep failed jobs
        "Archived": 90,   # Days to keep archived jobs before permanent deletion
        "Submitted": 2,   # Days to keep stalled jobs in Submitted state
        "Running": 7      # Days to keep stalled jobs in Running state
    },
    "archiving": {
        "enabled": True,
        "min_age_days": 7,       # Minimum age of jobs to consider for archiving
        "compress_results": True  # Whether to compress result files when archiving
    },
    "cleanup": {
        "enabled": True,
        "run_frequency_hours": 24,  # How often to run cleanup
        "max_jobs_per_run": 100     # Maximum jobs to process in a single cleanup run
    }
}

class JobLifecycleConfig:
    """
    Configuration for job lifecycle management.
    
    This class manages configuration for job retention, archiving, and cleanup policies.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize job lifecycle configuration.
        
        Args:
            config_path: Path to configuration file. If None, uses default config.
        """
        self.config = DEFAULT_CONFIG.copy()
        
        if config_path and os.path.exists(config_path):
            try:
                with open(config_path, 'r') as file:
                    user_config = yaml.safe_load(file)
                    
                # Update default config with user values
                if user_config:
                    self._update_nested_dict(self.config, user_config)
                    
                logger.info(f"Loaded job lifecycle config from {config_path}")
            except Exception as e:
                logger.error(f"Error loading config from {config_path}: {str(e)}")
    
    def _update_nested_dict(self, d: Dict[str, Any], u: Dict[str, Any]) -> Dict[str, Any]:
        """Recursively update a nested dictionary"""
        for k, v in u.items():
            if isinstance(v, dict) and k in d and isinstance(d[k], dict):
                self._update_nested_dict(d[k], v)
            else:
                d[k] = v
        return d
    
    def get_retention_days(self, status: str) -> int:
        """Get retention period for a job status in days"""
        return self.config["retention_periods"].get(status, 30)
    
    def is_archiving_enabled(self) -> bool:
        """Check if archiving is enabled"""
        return self.config["archiving"]["enabled"]
    
    def get_min_age_for_archiving(self) -> int:
        """Get minimum age in days for a job to be considered for archiving"""
        return self.config["archiving"]["min_age_days"]
    
    def should_compress_results(self) -> bool:
        """Check if result files should be compressed when archiving"""
        return self.config["archiving"]["compress_results"]
    
    def is_cleanup_enabled(self) -> bool:
        """Check if cleanup is enabled"""
        return self.config["cleanup"]["enabled"]
    
    def get_cleanup_frequency_hours(self) -> int:
        """Get how often cleanup should run in hours"""
        return self.config["cleanup"]["run_frequency_hours"]
    
    def get_max_jobs_per_cleanup(self) -> int:
        """Get maximum jobs to process in a single cleanup run"""
        return self.config["cleanup"]["max_jobs_per_run"]
    
    @classmethod
    def create_default_config_file(cls, output_path: str):
        """
        Create a default configuration file.
        
        Args:
            output_path: Path to write the default config
        """
        try:
            with open(output_path, 'w') as file:
                yaml.dump(DEFAULT_CONFIG, file, default_flow_style=False)
            logger.info(f"Created default config at {output_path}")
        except Exception as e:
            logger.error(f"Failed to create default config: {str(e)}")
            raise
