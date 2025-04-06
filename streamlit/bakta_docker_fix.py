#!/usr/bin/env python3
"""
Enhanced Bakta Docker Environment Handler

This module provides fixes for Bakta API integration in the Docker environment.
It addresses path mapping, async execution, and module import issues.
"""

import os
import sys
import logging
import asyncio
import importlib
from pathlib import Path
from typing import Dict, Any, Optional, Callable, Awaitable

# Configure logging
logging.basicConfig(level=logging.INFO,
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-docker-fix")

class BaktaDockerFix:
    """Helper class to fix Bakta module issues in Docker environment."""
    
    def __init__(self):
        self.is_docker = self._check_if_docker()
        self.module_ready = False
        
    def _check_if_docker(self) -> bool:
        """Check if we're running in a Docker container."""
        # Various ways to detect Docker
        if os.path.exists('/.dockerenv'):
            return True
        
        try:
            with open('/proc/1/cgroup', 'r') as f:
                return 'docker' in f.read()
        except:
            pass
            
        # Check for typical Docker environment variables
        if os.environ.get('DOCKER_CONTAINER', ''):
            return True
            
        # Default to safe assumption based on path structure
        if os.path.exists('/app/streamlit') and os.path.exists('/app/amr_predictor'):
            return True
            
        return False
    
    def fix_module_import(self) -> bool:
        """Fix module import issues in Docker environment."""
        logger.info(f"Fixing module import issues (Docker: {self.is_docker})")
        
        # Check if module is already importable
        try:
            import amr_predictor.bakta
            logger.info("✓ Bakta module already available through normal import")
            self.module_ready = True
            return True
        except ImportError:
            logger.warning("Bakta module not available through normal import")
        
        # Add potential module paths
        potential_paths = [
            "/app",
            os.path.join(os.path.dirname(os.path.dirname(__file__)), "amr_predictor"),
            os.path.dirname(os.path.dirname(__file__)),
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ]
        
        for path in potential_paths:
            if os.path.exists(path) and path not in sys.path:
                logger.info(f"Adding path to sys.path: {path}")
                sys.path.insert(0, path)
        
        # Try import again
        try:
            import amr_predictor.bakta
            logger.info("✓ Bakta module available after path modification")
            self.module_ready = True
            return True
        except ImportError as e:
            logger.error(f"Failed to import Bakta module: {str(e)}")
            return False
    
    def fix_docker_paths(self) -> None:
        """Fix Docker path mapping issues."""
        if not self.is_docker:
            logger.info("Not running in Docker, skipping path fixes")
            return
            
        logger.info("Fixing Docker path mapping issues")
        
        # Make sure results directory exists
        results_dir = os.environ.get("BAKTA_RESULTS_DIR", "/app/results/bakta")
        if not os.path.exists(results_dir):
            logger.info(f"Creating results directory: {results_dir}")
            os.makedirs(results_dir, exist_ok=True)
            
        # Create a path mapper function to add to sys.modules
        def docker_path_mapper(path: str) -> str:
            """Map paths between Docker containers."""
            # Implement path mapping based on memory knowledge about Docker volumes
            if '/app/results/' in path:
                # This is already correct for container-to-container communication
                return path
                
            return path
            
        # Add the path mapper to the sys.modules
        sys.modules['docker_path_mapper'] = type('', (), {'map_path': docker_path_mapper})()
        logger.info("✓ Docker path mapper installed")
    
    def fix_async_execution(self) -> None:
        """Configure asyncio for proper execution in Streamlit."""
        logger.info("Setting up async execution handler for Streamlit")
        
        # Create a helper function to run async functions
        def run_async(func: Callable[..., Awaitable[Any]], *args: Any, **kwargs: Any) -> Any:
            """Run an async function from synchronous Streamlit code."""
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                # If there's no event loop in the current thread, create one
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            return loop.run_until_complete(func(*args, **kwargs))
            
        # Add it to sys.modules for convenience
        sys.modules['streamlit_async'] = type('', (), {'run_async': run_async})()
        logger.info("✓ Streamlit async handler installed")
    
    def fix_environment_variables(self) -> None:
        """Ensure all required environment variables are properly set."""
        logger.info("Checking environment variables")
        
        # Default values for Docker environment
        defaults = {
            "BAKTA_API_URL": "https://bakta.computational.bio/api/v1",
            "BAKTA_RESULTS_DIR": "/app/results/bakta"
        }
        
        # Set defaults if not already set
        for var, default in defaults.items():
            if not os.environ.get(var):
                logger.info(f"Setting default for {var}: {default}")
                os.environ[var] = default
                
        # Log the current environment variables
        for var in defaults.keys():
            logger.info(f"{var} = {os.environ.get(var, 'Not set')}")
            
        # Make sure API key is set (but don't log the actual key)
        if not os.environ.get("BAKTA_API_KEY"):
            logger.warning("BAKTA_API_KEY is not set. API calls may fail.")
        else:
            logger.info("BAKTA_API_KEY is set.")
    
    def apply_all_fixes(self) -> bool:
        """Apply all fixes in the correct order."""
        logger.info("Applying all Bakta Docker fixes")
        
        # Order matters here
        self.fix_environment_variables()
        self.fix_docker_paths()
        module_fixed = self.fix_module_import()
        self.fix_async_execution()
        
        if module_fixed:
            logger.info("✓ All Bakta Docker fixes applied successfully")
        else:
            logger.error("✗ Failed to fix Bakta module import")
            
        return module_fixed

# Create a singleton instance
docker_fix = BaktaDockerFix()

# Apply all fixes when the module is imported
FIXES_APPLIED = docker_fix.apply_all_fixes()

# Provide convenience functions
def run_async(func, *args, **kwargs):
    """Convenience function to run async functions from Streamlit."""
    try:
        import streamlit_async
        return streamlit_async.run_async(func, *args, **kwargs)
    except ImportError:
        # Fall back to basic implementation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(func(*args, **kwargs))

def map_docker_path(path):
    """Convenience function to map paths between Docker containers."""
    try:
        import docker_path_mapper
        return docker_path_mapper.map_path(path)
    except ImportError:
        # Return as-is if mapper not available
        return path
