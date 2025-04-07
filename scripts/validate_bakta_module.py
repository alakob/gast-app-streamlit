#!/usr/bin/env python3
"""
Script to validate Bakta module availability and database connection.
This script will attempt to load the Bakta module and connect to the PostgreSQL database.
"""

import os
import sys
import logging
import importlib.util
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-validator")

def inspect_modules():
    """Inspect the Python module loading system"""
    logger.info("="*80)
    logger.info("PYTHON MODULE SEARCH PATHS:")
    for i, path in enumerate(sys.path):
        logger.info(f"  [{i}] {path}")
    
    logger.info("-"*80)
    logger.info("CHECKING FOR AMR_PREDICTOR MODULE:")
    for path in sys.path:
        potential_module = os.path.join(path, 'amr_predictor')
        if os.path.exists(potential_module):
            logger.info(f"  FOUND amr_predictor at: {potential_module}")
            
            bakta_path = os.path.join(potential_module, 'bakta')
            if os.path.exists(bakta_path):
                logger.info(f"  ✓ FOUND bakta module at {bakta_path}")
                
                init_file = os.path.join(bakta_path, "__init__.py")
                if os.path.exists(init_file):
                    logger.info(f"  ✓ Found __init__.py at {init_file}")
                    with open(init_file, 'r') as f:
                        first_line = f.readline().strip()
                        logger.info(f"  ✓ First line: {first_line}")
                else:
                    logger.warning(f"  ✗ No __init__.py found at {bakta_path}")
            else:
                logger.warning(f"  ✗ No bakta module at {potential_module}")
    
    logger.info("="*80)

def try_direct_import():
    """Try to directly import the Bakta module"""
    logger.info("ATTEMPTING DIRECT IMPORT:")
    
    try:
        import amr_predictor.bakta
        logger.info("✓ Successfully imported amr_predictor.bakta")
        
        # Check for expected components
        components = [
            "get_interface",
            "BaktaException",
            "BaktaApiError", 
            "create_config"
        ]
        
        for comp in components:
            if hasattr(amr_predictor.bakta, comp):
                logger.info(f"  ✓ Found component: {comp}")
            else:
                logger.warning(f"  ✗ Missing component: {comp}")
        
        # Try to create an interface
        logger.info("Attempting to create Bakta interface")
        interface = amr_predictor.bakta.get_interface()
        logger.info(f"  ✓ Created interface: {interface}")
        
        return True
    except ImportError as e:
        logger.error(f"✗ Failed to import amr_predictor.bakta: {str(e)}")
    except Exception as e:
        logger.error(f"✗ Error with Bakta module: {str(e)}")
    
    return False

def check_postgres():
    """Check PostgreSQL connection and Bakta tables"""
    logger.info("="*80)
    logger.info("CHECKING POSTGRESQL CONNECTION:")
    
    try:
        import psycopg2
        import psycopg2.extras
        
        logger.info("Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            host="postgres",
            database="amr_predictor_prod",
            user="postgres",
            password="postgres"
        )
        
        logger.info("✓ Connected to PostgreSQL")
        
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT tablename FROM pg_catalog.pg_tables 
                WHERE schemaname='public' AND tablename LIKE 'bakta%'
            """)
            
            tables = cursor.fetchall()
            logger.info(f"Found {len(tables)} Bakta tables:")
            
            for table in tables:
                logger.info(f"  ✓ {table[0]}")
                
                # Count rows in the table
                cursor.execute(f"SELECT COUNT(*) FROM {table[0]}")
                count = cursor.fetchone()[0]
                logger.info(f"    - Contains {count} records")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"✗ PostgreSQL error: {str(e)}")
        return False

def main():
    """Main entry point"""
    logger.info("Starting Bakta module and database validation")
    
    inspect_modules()
    module_ok = try_direct_import()
    db_ok = check_postgres()
    
    if module_ok:
        logger.info("✓ Bakta module validation PASSED")
    else:
        logger.error("✗ Bakta module validation FAILED")
    
    if db_ok:
        logger.info("✓ PostgreSQL validation PASSED")
    else:
        logger.error("✗ PostgreSQL validation FAILED")

if __name__ == "__main__":
    main()
