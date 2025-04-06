#!/usr/bin/env python3
"""
Database connection pool for PostgreSQL.

This module provides a connection pool for PostgreSQL database connections,
improving performance by reusing connections instead of creating new ones.
"""
import os
import threading
import logging
import time
import psycopg2
import psycopg2.pool
import psycopg2.extras
from typing import Dict, List, Any, Optional, Union
from contextlib import contextmanager
from urllib.parse import urlparse

# Configure logging
logger = logging.getLogger("database-pool")

class ConnectionPool:
    """
    Connection pool for PostgreSQL database connections.
    
    This class manages a pool of PostgreSQL connections to improve performance
    by reusing connections rather than creating new ones for each query.
    """
    
    def __init__(self, db_url: str, min_connections: int = 2, max_connections: int = 5, 
                timeout: float = 30.0):
        """
        Initialize the connection pool.
        
        Args:
            db_url: PostgreSQL connection URL (postgres://user:pass@host:port/dbname)
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections in the pool
            timeout: Timeout in seconds for acquiring a connection
        """
        self.db_url = db_url
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.timeout = timeout
        
        # Parse connection parameters from URL
        url = urlparse(db_url)
        self.db_params = {
            'dbname': url.path[1:],
            'user': url.username,
            'password': url.password,
            'host': url.hostname,
            'port': url.port or 5432
        }
        
        # Initialize the connection pool using psycopg2's built-in pooling
        self.pool = psycopg2.pool.ThreadedConnectionPool(
            minconn=min_connections,
            maxconn=max_connections,
            **self.db_params
        )
        
        # Track connections in use by thread
        self.in_use: Dict[int, Any] = {}
        self.lock = threading.RLock()
        
        logger.info(f"Initialized PostgreSQL connection pool with {min_connections}-{max_connections} connections to {url.hostname}:{url.port}/{url.path[1:]}")
    
    def _check_connection(self, conn):
        """Check if a connection is still alive and reset it if needed"""
        try:
            # Execute a simple query to check connection
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            return True
        except psycopg2.OperationalError:
            logger.warning("Found stale connection, will be replaced")
            return False
    
    def _setup_connection(self, conn):
        """Set up a newly acquired connection with proper settings"""
        # Set session parameters for better performance and consistency
        cursor = conn.cursor()
        
        # Ensure transactions are properly isolated
        cursor.execute("SET SESSION CHARACTERISTICS AS TRANSACTION ISOLATION LEVEL READ COMMITTED")
        
        # Set statement timeout to prevent long-running queries
        cursor.execute("SET statement_timeout = '30s'")
        
        # Set reasonable work memory for complex operations
        cursor.execute("SET work_mem = '16MB'")
        
        # Configure the connection to return dictionaries
        conn.cursor_factory = psycopg2.extras.RealDictCursor
        
        cursor.close()
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        This context manager acquires a connection from the pool and
        returns it to the pool when the context is exited.
        
        Returns:
            A PostgreSQL database connection
            
        Raises:
            TimeoutError: If no connection could be acquired within the timeout
            psycopg2.OperationalError: If there's a database connection error
        """
        conn = self._acquire_connection()
        thread_id = threading.get_ident()
        
        try:
            yield conn
        except Exception as e:
            # If we get a connection error, mark the connection as broken
            if isinstance(e, psycopg2.OperationalError):
                logger.error(f"Database operation error: {str(e)}")
                self.pool.putconn(conn, close=True)  # Return as broken connection
                self.in_use.pop(thread_id, None)
            raise
        finally:
            # Only release if it wasn't already released due to error
            if thread_id in self.in_use:
                self._release_connection(thread_id, conn)
    
    def _acquire_connection(self):
        """
        Acquire a connection from the pool.
        
        Returns:
            A PostgreSQL database connection
            
        Raises:
            TimeoutError: If no connection could be acquired within the timeout
            psycopg2.OperationalError: If a database error occurs
        """
        thread_id = threading.get_ident()
        
        # If this thread already has a connection, return it
        with self.lock:
            if thread_id in self.in_use:
                conn = self.in_use[thread_id]
                if self._check_connection(conn):
                    return conn
                # Connection is stale, remove it and get a new one
                self.in_use.pop(thread_id)
        
        start_time = time.time()
        
        while True:
            # Check timeout
            if time.time() - start_time > self.timeout:
                logger.error(f"Timeout acquiring connection after {self.timeout} seconds")
                raise TimeoutError(f"Timeout acquiring connection after {self.timeout} seconds")
            
            try:
                with self.lock:
                    # Get connection from psycopg2's pool
                    conn = self.pool.getconn(key=thread_id)
                    self.in_use[thread_id] = conn
                    return self._setup_connection(conn)
            except psycopg2.pool.PoolError:
                # Pool is at capacity, wait and retry
                time.sleep(0.1)
            except psycopg2.OperationalError as e:
                # Database error, log and retry
                logger.error(f"Database error when acquiring connection: {str(e)}")
                time.sleep(0.5)  # Wait a bit longer on operational errors
    
    def _release_connection(self, thread_id: int, conn):
        """
        Release a connection back to the pool.
        
        Args:
            thread_id: ID of the thread that acquired the connection
            conn: The connection to release
        """
        with self.lock:
            # Remove from in_use
            if thread_id in self.in_use:
                del self.in_use[thread_id]
            
            # Return to psycopg2's connection pool
            try:
                self.pool.putconn(conn, key=thread_id, close=False)
            except Exception as e:
                logger.warning(f"Error returning connection to pool: {str(e)}")
                # Try to close the connection if we can't return it to the pool
                try:
                    conn.close()
                except Exception:
                    pass
    
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            try:
                # Close all connections using psycopg2's pool manager
                self.pool.closeall()
                
                # Clear the in-use tracking
                self.in_use.clear()
                
                logger.info("Closed all connections in the pool")
            except Exception as e:
                logger.error(f"Error closing all connections: {str(e)}")

# Global connection pool instance for each environment
_connection_pools = {}

def get_connection_pool(db_url: str = None, min_connections: int = 2, 
                      max_connections: int = 10, environment: str = 'prod') -> ConnectionPool:
    """
    Get a connection pool instance for the specified environment.
    
    This function returns a connection pool for the specified environment,
    creating it if necessary. This allows separate pools for dev, test, and prod.
    
    Args:
        db_url: PostgreSQL connection URL (required on first call for an environment)
        min_connections: Minimum number of connections to maintain
        max_connections: Maximum number of connections in the pool
        environment: Environment name ('dev', 'test', or 'prod')
        
    Returns:
        The connection pool for the specified environment
        
    Raises:
        ValueError: If db_url is not provided on first call for an environment
    """
    global _connection_pools
    
    if environment not in _connection_pools or _connection_pools[environment] is None:
        if db_url is None:
            raise ValueError(f"db_url must be provided when creating the {environment} connection pool")
            
        _connection_pools[environment] = ConnectionPool(
            db_url=db_url,
            min_connections=min_connections,
            max_connections=max_connections
        )
        
    return _connection_pools[environment]

@contextmanager
def get_connection(db_url: str = None, environment: str = 'prod'):
    """
    Get a connection from the pool for the specified environment.
    
    This context manager acquires a connection from the pool and
    returns it to the pool when the context is exited.
    
    Args:
        db_url: PostgreSQL connection URL (required on first call for an environment)
        environment: Environment name ('dev', 'test', or 'prod')
        
    Returns:
        A PostgreSQL database connection
        
    Raises:
        ValueError: If db_url is not provided on first call for an environment
        TimeoutError: If connection acquisition times out
        psycopg2.Error: If a database error occurs
    """
    pool = get_connection_pool(db_url, environment=environment)
    with pool.get_connection() as conn:
        yield conn
