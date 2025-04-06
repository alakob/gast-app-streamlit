#!/usr/bin/env python3
"""
Job Association Utilities for the GAST App.

This module provides functions to manage associations between AMR and Bakta jobs.
"""

import os
import sys
import logging
import psycopg2
from dotenv import load_dotenv
from typing import Dict, Optional, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

def get_db_connection():
    """Get a database connection based on environment variables"""
    # Get PostgreSQL connection parameters
    pg_host = os.getenv('PG_HOST', 'localhost')
    pg_port = os.getenv('PG_PORT', '5432')
    pg_user = os.getenv('PG_USER', 'postgres')
    pg_password = os.getenv('PG_PASSWORD', '')
    
    # Get environment (dev, test, or prod)
    environment = os.getenv('ENVIRONMENT', 'dev')
    
    # Get database name based on environment
    if environment == 'dev':
        database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
    elif environment == 'test':
        database = os.getenv('PG_DATABASE_TEST', 'amr_predictor_test')
    elif environment == 'prod':
        database = os.getenv('PG_DATABASE_PROD', 'amr_predictor_prod')
    else:
        logger.warning(f"Unknown environment: {environment}, defaulting to dev")
        database = os.getenv('PG_DATABASE_DEV', 'amr_predictor_dev')
    
    try:
        conn = psycopg2.connect(
            host=pg_host,
            port=pg_port,
            user=pg_user,
            password=pg_password,
            database=database
        )
        return conn
    except Exception as e:
        logger.error(f"Error connecting to database: {str(e)}")
        raise

def associate_jobs(amr_job_id: str, bakta_job_id: str) -> bool:
    """
    Associate an AMR job with a Bakta job in the database.
    
    Args:
        amr_job_id: ID of the AMR job
        bakta_job_id: ID of the Bakta job
        
    Returns:
        bool: True if successful, False otherwise
    """
    logger.info(f"Associating AMR job {amr_job_id} with Bakta job {bakta_job_id}")
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Update the AMR job to include the Bakta job ID
        cursor.execute("""
            UPDATE amr_jobs
            SET bakta_job_id = %s
            WHERE id = %s
        """, (bakta_job_id, amr_job_id))
        
        # Commit the changes
        conn.commit()
        
        # Check if any rows were affected
        rows_affected = cursor.rowcount
        if rows_affected == 0:
            logger.warning(f"No AMR job found with ID {amr_job_id}")
            return False
            
        logger.info(f"Successfully associated AMR job {amr_job_id} with Bakta job {bakta_job_id}")
        return True
    except Exception as e:
        logger.error(f"Error associating jobs: {str(e)}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_associated_bakta_job(amr_job_id: str) -> Optional[str]:
    """
    Get the Bakta job ID associated with an AMR job.
    
    Args:
        amr_job_id: ID of the AMR job
        
    Returns:
        str or None: Bakta job ID if found, None otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the Bakta job ID from the AMR job
        cursor.execute("""
            SELECT bakta_job_id
            FROM amr_jobs
            WHERE id = %s
        """, (amr_job_id,))
        
        result = cursor.fetchone()
        if result is None or result[0] is None:
            return None
            
        return result[0]
    except Exception as e:
        logger.error(f"Error getting associated Bakta job: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def get_associated_amr_job(bakta_job_id: str) -> Optional[str]:
    """
    Get the AMR job ID associated with a Bakta job.
    
    Args:
        bakta_job_id: ID of the Bakta job
        
    Returns:
        str or None: AMR job ID if found, None otherwise
    """
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get the AMR job ID associated with the Bakta job
        cursor.execute("""
            SELECT id
            FROM amr_jobs
            WHERE bakta_job_id = %s
        """, (bakta_job_id,))
        
        result = cursor.fetchone()
        if result is None:
            return None
            
        return result[0]
    except Exception as e:
        logger.error(f"Error getting associated AMR job: {str(e)}")
        return None
    finally:
        if conn:
            conn.close()

def update_session_associations(session_state: Any) -> None:
    """
    Update session state with job associations.
    This helps maintain consistent state in the Streamlit app.
    
    Args:
        session_state: Streamlit session state object
    """
    # Initialize association dict if not present
    if "job_associations" not in session_state:
        session_state.job_associations = {}
    
    # Check if we have both AMR and Bakta job IDs in the session
    amr_job_id = session_state.get("amr_job_id")
    bakta_job_id = session_state.get("bakta_job_id")
    
    if amr_job_id and bakta_job_id:
        # Store bidirectional mapping
        session_state.job_associations[amr_job_id] = bakta_job_id
        session_state.job_associations[bakta_job_id] = amr_job_id
        logger.info(f"Updated session state job associations: AMR {amr_job_id} <-> Bakta {bakta_job_id}")
