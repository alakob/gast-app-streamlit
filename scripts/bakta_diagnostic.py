#!/usr/bin/env python3
"""
Diagnostic script to verify Bakta API connectivity in Docker container.
This script runs simple tests to identify potential issues with the Bakta API integration.
"""

import os
import sys
import json
import logging
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-diagnostic")

def test_environment_variables():
    """Test if all required environment variables are set and accessible."""
    logger.info("Testing environment variables...")
    
    # Required variables
    required_vars = [
        "BAKTA_API_URL", 
        "BAKTA_API_KEY",
        "BAKTA_RESULTS_DIR"
    ]
    
    # Check each variable
    missing_vars = []
    for var in required_vars:
        value = os.environ.get(var)
        if value:
            logger.info(f"✓ {var} = {value}")
        else:
            logger.error(f"✗ {var} is not set")
            missing_vars.append(var)
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        return False
    
    logger.info("All required environment variables are set.")
    return True

def test_api_connection():
    """Test if the Bakta API is accessible."""
    logger.info("Testing API connection...")
    
    base_url = os.environ.get("BAKTA_API_URL", "")
    api_key = os.environ.get("BAKTA_API_KEY", "")
    
    if not base_url:
        logger.error("Cannot test API connection: BAKTA_API_URL is not set")
        return False
    
    # Test connection
    try:
        # Adjust the URL to use a health check endpoint if available
        # Otherwise, we'll just try to hit the base API URL
        test_url = base_url
        if not test_url.endswith("/"):
            test_url += "/"
        
        headers = {}
        if api_key:
            headers["X-API-Key"] = api_key
        
        logger.info(f"Attempting to connect to {test_url}")
        response = requests.get(test_url, headers=headers, timeout=10)
        
        logger.info(f"Response status code: {response.status_code}")
        logger.info(f"Response headers: {json.dumps(dict(response.headers), indent=2)}")
        
        try:
            logger.info(f"Response content: {json.dumps(response.json(), indent=2)}")
        except:
            logger.info(f"Response content: {response.text[:500]}...")
        
        if response.status_code < 400:
            logger.info("API connection successful")
            return True
        else:
            logger.error(f"API connection failed with status code {response.status_code}")
            return False
            
    except Exception as e:
        logger.error(f"Error connecting to API: {str(e)}")
        return False

def test_result_directory():
    """Test if the results directory exists and is writable."""
    logger.info("Testing results directory...")
    
    results_dir = os.environ.get("BAKTA_RESULTS_DIR", "")
    
    if not results_dir:
        logger.error("Cannot test results directory: BAKTA_RESULTS_DIR is not set")
        return False
    
    # Check if directory exists
    results_path = Path(results_dir)
    if not results_path.exists():
        logger.warning(f"Results directory does not exist: {results_dir}")
        
        # Try to create it
        try:
            logger.info(f"Attempting to create results directory: {results_dir}")
            results_path.mkdir(parents=True, exist_ok=True)
            logger.info(f"✓ Created results directory: {results_dir}")
        except Exception as e:
            logger.error(f"Failed to create results directory: {str(e)}")
            return False
    
    # Check if directory is writable
    try:
        test_file = results_path / "bakta_test_file.txt"
        with open(test_file, "w") as f:
            f.write("Test file for Bakta results directory")
        
        logger.info(f"✓ Successfully wrote to results directory")
        
        # Clean up test file
        test_file.unlink()
        logger.info(f"✓ Successfully removed test file")
        
        return True
    except Exception as e:
        logger.error(f"Failed to write to results directory: {str(e)}")
        return False

def test_module_import():
    """Test if the Bakta module can be imported."""
    logger.info("Testing Bakta module import...")
    
    try:
        # First try directly
        try:
            import amr_predictor.bakta
            logger.info("✓ Bakta module imported successfully via direct import")
            logger.info(f"Bakta module path: {amr_predictor.bakta.__file__}")
            return True
        except ImportError as e:
            logger.warning(f"Direct import failed: {str(e)}")
        
        # Try importing after adding potential paths
        potential_paths = [
            "/app",
            "/app/amr_predictor",
            os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        ]
        
        for path in potential_paths:
            if path not in sys.path:
                logger.info(f"Adding path to sys.path: {path}")
                sys.path.insert(0, path)
        
        import amr_predictor.bakta
        logger.info("✓ Bakta module imported successfully after path modification")
        logger.info(f"Bakta module path: {amr_predictor.bakta.__file__}")
        return True
    
    except ImportError as e:
        logger.error(f"Failed to import Bakta module: {str(e)}")
        
        # List all modules in sys.modules matching 'bakta'
        bakta_modules = {name: module for name, module in sys.modules.items() if 'bakta' in name.lower()}
        logger.info(f"Bakta-related modules in sys.modules: {list(bakta_modules.keys())}")
        
        return False

def test_mock_vs_real():
    """Test if we're using a real or mock Bakta implementation."""
    logger.info("Testing if we're using a real or mock Bakta implementation...")
    
    try:
        import amr_predictor.bakta
        
        # Check for telltale signs of a mock implementation
        if hasattr(amr_predictor.bakta, 'MOCK_IMPLEMENTATION'):
            logger.warning("Using mock Bakta implementation (explicit flag)")
            return False
        
        # Try to access real module functions
        real_module_attrs = [
            "client", "BaktaClient", "BaktaJobManager", "BaktaJob", 
            "BaktaAnnotation", "BaktaException"
        ]
        
        missing_attrs = []
        for attr in real_module_attrs:
            if not hasattr(amr_predictor.bakta, attr):
                missing_attrs.append(attr)
        
        if missing_attrs:
            logger.warning(f"Missing attributes from real implementation: {', '.join(missing_attrs)}")
            logger.warning("Likely using a mock or incomplete implementation")
            return False
        
        logger.info("✓ Using real Bakta implementation")
        return True
        
    except ImportError:
        logger.error("Cannot test implementation: Bakta module not importable")
        return False

def test_standalone_vs_module():
    """Compare standalone script with module implementation."""
    logger.info("Comparing standalone script with module implementation...")
    
    standalone_script = Path(__file__).parent / "submit_bakta.py"
    if not standalone_script.exists():
        logger.warning(f"Standalone script not found: {standalone_script}")
        return
    
    try:
        with open(standalone_script) as f:
            standalone_content = f.read()
        
        # Look for key differences
        if "api_key" not in standalone_content.lower() and "BAKTA_API_KEY" not in standalone_content:
            logger.warning("Standalone script doesn't use API key authentication")
        
        if "token" not in standalone_content.lower():
            logger.warning("Standalone script doesn't use token-based authentication")
        
        if "async" not in standalone_content.lower():
            logger.info("Standalone script uses synchronous functions (vs async in module)")
        
        # Check for different URLs
        import re
        urls_in_script = re.findall(r'https?://[^\s"\']+', standalone_content)
        logger.info(f"URLs found in standalone script: {urls_in_script}")
        
        module_url = os.environ.get("BAKTA_API_URL", "")
        if module_url and module_url not in urls_in_script:
            logger.warning(f"Module uses different URL ({module_url}) than standalone script")
        
    except Exception as e:
        logger.error(f"Error comparing scripts: {str(e)}")

def run_all_tests():
    """Run all diagnostic tests."""
    tests = [
        test_environment_variables,
        test_api_connection,
        test_result_directory,
        test_module_import,
        test_mock_vs_real,
        test_standalone_vs_module
    ]
    
    results = {}
    
    for test in tests:
        test_name = test.__name__
        logger.info(f"\n{'='*50}\nRunning test: {test_name}\n{'='*50}")
        try:
            result = test()
            results[test_name] = result
        except Exception as e:
            logger.error(f"Error running test {test_name}: {str(e)}")
            results[test_name] = False
    
    # Print summary
    logger.info("\n\n=========== DIAGNOSTIC SUMMARY ===========")
    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        logger.info(f"{status} - {test_name}")
    
    if all(results.values()):
        logger.info("\n✓ All tests passed!")
    else:
        failed_tests = [name for name, result in results.items() if not result]
        logger.warning(f"\n✗ {len(failed_tests)} tests failed: {', '.join(failed_tests)}")

if __name__ == "__main__":
    logger.info("Starting Bakta diagnostic tests...")
    run_all_tests()
