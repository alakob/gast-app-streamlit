#!/usr/bin/env python3
"""
Scheduled task runner for AMR jobs maintenance.

This module provides a scheduler for running maintenance tasks
like job archiving and cleanup at regular intervals.
"""
import os
import time
import logging
import threading
import schedule
from typing import Callable, Dict, Any, Optional
from datetime import datetime

from amr_predictor.bakta.database import DatabaseManager
from amr_predictor.config.job_lifecycle_config import JobLifecycleConfig
from amr_predictor.maintenance.job_archiver import JobArchiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("scheduled-tasks")

class MaintenanceScheduler:
    """
    Scheduler for maintenance tasks.
    
    This class schedules and runs maintenance tasks like
    job archiving and cleanup at configured intervals.
    """
    
    def __init__(self, config_path: Optional[str] = None, db_path: Optional[str] = None):
        """
        Initialize the maintenance scheduler.
        
        Args:
            config_path: Path to job lifecycle configuration
            db_path: Path to database
        """
        self.config = JobLifecycleConfig(config_path)
        self.db_manager = DatabaseManager(db_path)
        self.job_archiver = JobArchiver(self.config, self.db_manager)
        
        self.running = False
        self.thread = None
        
        # Set up schedules based on configuration
        self._setup_schedules()
    
    def _setup_schedules(self):
        """Set up scheduled tasks based on configuration"""
        # Clear existing schedules
        schedule.clear()
        
        # Schedule archiving task
        if self.config.is_archiving_enabled():
            # Archive daily at midnight
            schedule.every().day.at("00:00").do(self.run_archiving)
            logger.info("Scheduled daily archiving task at midnight")
        
        # Schedule cleanup task
        if self.config.is_cleanup_enabled():
            hours = self.config.get_cleanup_frequency_hours()
            
            if hours == 24:
                # Run daily at 1 AM
                schedule.every().day.at("01:00").do(self.run_cleanup)
                logger.info("Scheduled daily cleanup task at 1 AM")
            else:
                # Run every X hours
                schedule.every(hours).hours.do(self.run_cleanup)
                logger.info(f"Scheduled cleanup task every {hours} hours")
    
    def run_archiving(self):
        """Run the archiving task"""
        try:
            logger.info("Starting scheduled archiving task")
            max_jobs = self.config.get_max_jobs_per_cleanup()
            archived_count = self.job_archiver.archive_old_jobs(max_jobs)
            logger.info(f"Archiving task completed: {archived_count} jobs archived")
            return archived_count
        except Exception as e:
            logger.error(f"Error in archiving task: {str(e)}")
            return 0
    
    def run_cleanup(self):
        """Run the cleanup task"""
        try:
            logger.info("Starting scheduled cleanup task")
            max_jobs = self.config.get_max_jobs_per_cleanup()
            total, details = self.job_archiver.cleanup_old_jobs(max_jobs)
            logger.info(f"Cleanup task completed: {total} jobs cleaned up")
            return total
        except Exception as e:
            logger.error(f"Error in cleanup task: {str(e)}")
            return 0
    
    def _run_scheduler(self):
        """Run the scheduler loop in a thread"""
        logger.info("Maintenance scheduler started")
        
        while self.running:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
            
        logger.info("Maintenance scheduler stopped")
    
    def start(self):
        """Start the scheduler"""
        if self.running:
            logger.warning("Scheduler is already running")
            return
            
        self.running = True
        self.thread = threading.Thread(target=self._run_scheduler)
        self.thread.daemon = True  # Allow the program to exit even if the thread is running
        self.thread.start()
        
        logger.info("Maintenance scheduler started")
    
    def stop(self):
        """Stop the scheduler"""
        if not self.running:
            logger.warning("Scheduler is not running")
            return
            
        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
            
        logger.info("Maintenance scheduler stopped")

# Convenience function to run maintenance tasks once
def run_maintenance_tasks(config_path: Optional[str] = None, db_path: Optional[str] = None):
    """
    Run maintenance tasks once (non-scheduled).
    
    Args:
        config_path: Path to job lifecycle configuration
        db_path: Path to database
        
    Returns:
        Results from archiving and cleanup tasks
    """
    try:
        # Initialize components
        config = JobLifecycleConfig(config_path)
        db_manager = DatabaseManager(db_path)
        job_archiver = JobArchiver(config, db_manager)
        
        results = {}
        
        # Run archiving if enabled
        if config.is_archiving_enabled():
            logger.info("Running archiving task")
            max_jobs = config.get_max_jobs_per_cleanup()
            archived_count = job_archiver.archive_old_jobs(max_jobs)
            results["archived"] = archived_count
            
        # Run cleanup if enabled
        if config.is_cleanup_enabled():
            logger.info("Running cleanup task")
            max_jobs = config.get_max_jobs_per_cleanup()
            total, details = job_archiver.cleanup_old_jobs(max_jobs)
            results["cleaned_up"] = total
            results["cleanup_details"] = details
            
        return results
        
    except Exception as e:
        logger.error(f"Error running maintenance tasks: {str(e)}")
        return {"error": str(e)}

# Main function for running as script
def main():
    """Main function for running the scheduler as a script"""
    import argparse
    import sys
    import signal
    
    parser = argparse.ArgumentParser(description="Run AMR job maintenance tasks")
    parser.add_argument("--config", help="Path to job lifecycle configuration file")
    parser.add_argument("--db", help="Path to database file")
    parser.add_argument("--run-once", action="store_true", help="Run tasks once and exit")
    
    args = parser.parse_args()
    
    if args.run_once:
        # Run tasks once
        results = run_maintenance_tasks(args.config, args.db)
        print(f"Maintenance tasks completed: {results}")
        return
        
    # Set up the scheduler
    scheduler = MaintenanceScheduler(args.config, args.db)
    
    # Set up signal handlers for graceful shutdown
    def signal_handler(sig, frame):
        print("Shutting down scheduler...")
        scheduler.stop()
        sys.exit(0)
        
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start the scheduler
    scheduler.start()
    
    # Keep the main thread alive
    try:
        while True:
            time.sleep(1)
    except (KeyboardInterrupt, SystemExit):
        scheduler.stop()

if __name__ == "__main__":
    main()
