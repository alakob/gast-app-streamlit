#!/usr/bin/env python3
"""
Script to fix Bakta integration and database connections.
This script ensures proper database connections and real module usage.
"""

import os
import sys
import importlib
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("bakta-fixer")

def setup_env_variables():
    """Setup environment variables for real mode"""
    os.environ["BAKTA_USE_REAL_API"] = "1"
    os.environ["PYTHONPATH"] = "/app:" + os.environ.get("PYTHONPATH", "")
    logger.info("✓ Setup environment variables for real API mode")

def verify_bakta_module():
    """Verify Bakta module is importable"""
    try:
        import amr_predictor.bakta
        logger.info(f"✓ Successfully imported amr_predictor.bakta")
        
        # Test key components
        components = [
            "get_interface", 
            "BaktaException",
            "BaktaApiError",
            "create_config",
            "DatabaseManager"  # Critical for database operations
        ]
        
        for comp in components:
            if hasattr(amr_predictor.bakta, comp):
                logger.info(f"  ✓ Found component: {comp}")
            else:
                logger.error(f"  ✗ Missing component: {comp}")
                return False
        
        return True
    except ImportError as e:
        logger.error(f"✗ Failed to import amr_predictor.bakta: {str(e)}")
        return False

def verify_postgres_connection():
    """Verify the PostgreSQL connection and Bakta tables"""
    try:
        import psycopg2
        
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
            if not tables:
                logger.error("✗ No Bakta tables found in PostgreSQL")
                return False
                
            logger.info(f"Found {len(tables)} Bakta tables:")
            for table in tables:
                logger.info(f"  ✓ {table[0]}")
        
        # Create a test record to verify write capability
        with conn.cursor() as cursor:
            try:
                # Create a test job entry
                cursor.execute("""
                    INSERT INTO bakta_jobs (
                        id, name, secret, status, fasta_path, config, created_at, updated_at
                    ) VALUES (
                        'test-integration-job', 'Integration Test', 'test-secret', 
                        'CREATED', '/tmp/test.fasta', '{"test": true}', 
                        NOW(), NOW()
                    ) ON CONFLICT (id) DO NOTHING
                """)
                conn.commit()
                logger.info("✓ Successfully created test job entry in database")
            except Exception as e:
                logger.error(f"✗ Failed to create test job: {str(e)}")
                return False
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"✗ PostgreSQL error: {str(e)}")
        return False

def fix_api_client_file():
    """Fix the API client to ensure Bakta module is properly used"""
    api_client_path = Path("/app/streamlit/api_client.py")
    
    if not api_client_path.exists():
        logger.error(f"✗ API client file not found: {api_client_path}")
        return False
    
    logger.info(f"Modifying API client file: {api_client_path}")
    
    try:
        # Read content
        content = api_client_path.read_text()
        
        # Make replacements to ensure real implementation
        replacements = [
            # Ensure BAKTA_AVAILABLE is always True
            ("BAKTA_AVAILABLE = False", "BAKTA_AVAILABLE = True  # Force real implementation"),
            
            # Ensure interface creation prioritizes real connections
            ("if self.interface is None:", "if True:  # Always use real DatabaseManager"),
            
            # Comment out mock warnings
            ("logger.warning(\"Bakta module not available", "# logger.warning(\"Bakta module not available"),
            
            # Add proper database connection to BaktaApiWrapper.__init__
            ("def __init__(self):", """def __init__(self):
        \"\"\"Initialize the Bakta API wrapper using the unified interface.\"\"\"
        # Force real mode
        import os
        os.environ["BAKTA_USE_REAL_API"] = "1"
        import streamlit as st
        st.session_state["using_real_bakta_api"] = True
        
        # Always create a real interface
        self.interface = get_interface()
        
        # Initialize database manager directly
        try:
            from amr_predictor.bakta.database_postgres import DatabaseManager
            self.db_manager = DatabaseManager(environment='prod')
            logger.info("✓ Successfully created database manager directly")
        except Exception as e:
            logger.warning(f"Could not create database manager: {str(e)}")
            self.db_manager = None""")
        ]
        
        # Apply replacements
        for old, new in replacements:
            if old in content:
                content = content.replace(old, new)
                logger.info(f"✓ Replaced: {old}")
            else:
                logger.warning(f"✗ String not found: {old}")
        
        # Write back the modified content
        api_client_path.write_text(content)
        logger.info("✓ Successfully updated API client file")
        
        # Verify changes were successful
        modified_content = api_client_path.read_text()
        success = all(new in modified_content for _, new in replacements if not new.startswith('#'))
        if success:
            logger.info("✓ Verified all modifications were applied")
        else:
            logger.warning("✗ Some modifications were not applied correctly")
        
        return success
    except Exception as e:
        logger.error(f"✗ Failed to modify API client: {str(e)}")
        return False

def main():
    """Main entry point"""
    logger.info("Starting Bakta integration fix")
    
    setup_env_variables()
    
    # Verify Bakta module 
    module_ok = verify_bakta_module()
    if not module_ok:
        logger.error("✗ Bakta module verification failed - cannot proceed")
        sys.exit(1)
    
    # Verify database connection
    db_ok = verify_postgres_connection()
    if not db_ok:
        logger.error("✗ PostgreSQL verification failed - cannot proceed")
        sys.exit(1)
    
    # Fix API client code
    api_fixed = fix_api_client_file()
    if not api_fixed:
        logger.error("✗ API client fix failed - integration may not work")
        sys.exit(1)
    
    logger.info("✓ All fixes applied successfully")
    logger.info("✓ Bakta integration should now use real implementation and database")

if __name__ == "__main__":
    main()
