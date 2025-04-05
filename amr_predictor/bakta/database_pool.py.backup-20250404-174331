#!/usr/bin/env python3
"""
Database connection pool for SQLite.

This module provides a connection pool for SQLite database connections,
improving performance by reusing connections instead of creating new ones.
"""
import os
import sqlite3
import threading
import logging
import time
from typing import Dict, List, Any, Optional
from contextlib import contextmanager

# Configure logging
logger = logging.getLogger("database-pool")

class ConnectionPool:
    """
    Connection pool for SQLite database connections.
    
    This class manages a pool of SQLite connections to improve performance
    by reusing connections rather than creating new ones for each query.
    """
    
    def __init__(self, db_path: str, min_connections: int = 2, max_connections: int = 5, 
                timeout: float = 30.0):
        """
        Initialize the connection pool.
        
        Args:
            db_path: Path to the SQLite database
            min_connections: Minimum number of connections to maintain
            max_connections: Maximum number of connections in the pool
            timeout: Timeout in seconds for acquiring a connection
        """
        self.db_path = db_path
        self.min_connections = min_connections
        self.max_connections = max_connections
        self.timeout = timeout
        
        # Initialize pool
        self.pool: List[sqlite3.Connection] = []
        self.in_use: Dict[int, sqlite3.Connection] = {}
        self.lock = threading.RLock()
        
        # Initialize with minimum connections
        self._initialize_pool()
        
        logger.info(f"Initialized connection pool with {min_connections} connections to {db_path}")
    
    def _initialize_pool(self):
        """Initialize the pool with the minimum number of connections"""
        with self.lock:
            for _ in range(self.min_connections):
                conn = self._create_connection()
                self.pool.append(conn)
    
    def _create_connection(self) -> sqlite3.Connection:
        """Create a new database connection"""
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Return rows as dictionaries
        
        # Enable foreign keys
        conn.execute("PRAGMA foreign_keys = ON")
        
        # Performance optimizations
        # Use WAL mode for better concurrency
        conn.execute("PRAGMA journal_mode = WAL")
        # Set a reasonable cache size
        conn.execute("PRAGMA cache_size = 10000")
        # Synchronous mode for better performance with reasonable safety
        conn.execute("PRAGMA synchronous = NORMAL")
        
        return conn
    
    @contextmanager
    def get_connection(self):
        """
        Get a connection from the pool.
        
        This context manager acquires a connection from the pool and
        returns it to the pool when the context is exited.
        
        Returns:
            A database connection
            
        Raises:
            TimeoutError: If no connection could be acquired within the timeout
        """
        conn = self._acquire_connection()
        thread_id = threading.get_ident()
        
        try:
            yield conn
        finally:
            self._release_connection(thread_id, conn)
    
    def _acquire_connection(self) -> sqlite3.Connection:
        """
        Acquire a connection from the pool.
        
        Returns:
            A database connection
            
        Raises:
            TimeoutError: If no connection could be acquired within the timeout
        """
        thread_id = threading.get_ident()
        
        # If this thread already has a connection, return it
        with self.lock:
            if thread_id in self.in_use:
                return self.in_use[thread_id]
        
        start_time = time.time()
        
        while True:
            # Check timeout
            if time.time() - start_time > self.timeout:
                logger.error(f"Timeout acquiring connection after {self.timeout} seconds")
                raise TimeoutError(f"Timeout acquiring connection after {self.timeout} seconds")
            
            with self.lock:
                # Check if we have a connection in the pool
                if self.pool:
                    # Get a connection from the pool
                    conn = self.pool.pop(0)
                    self.in_use[thread_id] = conn
                    return conn
                
                # If we haven't reached the max connections, create a new one
                if len(self.in_use) < self.max_connections:
                    conn = self._create_connection()
                    self.in_use[thread_id] = conn
                    return conn
            
            # No connections available, wait and try again
            time.sleep(0.1)
    
    def _release_connection(self, thread_id: int, conn: sqlite3.Connection):
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
                
            # Add back to pool if we're not over min_connections
            if len(self.pool) < self.min_connections:
                self.pool.append(conn)
            else:
                # Close excess connections
                conn.close()
    
    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            # Close all connections in the pool
            for conn in self.pool:
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {str(e)}")
            
            # Close all in-use connections
            for conn in self.in_use.values():
                try:
                    conn.close()
                except Exception as e:
                    logger.warning(f"Error closing in-use connection: {str(e)}")
            
            # Clear collections
            self.pool.clear()
            self.in_use.clear()
            
        logger.info("Closed all connections in the pool")

# Global connection pool instance
_connection_pool = None

def get_connection_pool(db_path: str = None, min_connections: int = 2, 
                      max_connections: int = 5) -> ConnectionPool:
    """
    Get the global connection pool instance.
    
    This function returns the global connection pool, creating it if necessary.
    
    Args:
        db_path: Path to the SQLite database (required on first call)
        min_connections: Minimum number of connections to maintain
        max_connections: Maximum number of connections in the pool
        
    Returns:
        The connection pool
        
    Raises:
        ValueError: If db_path is not provided on first call
    """
    global _connection_pool
    
    if _connection_pool is None:
        if db_path is None:
            raise ValueError("db_path must be provided when creating the connection pool")
            
        _connection_pool = ConnectionPool(
            db_path=db_path,
            min_connections=min_connections,
            max_connections=max_connections
        )
        
    return _connection_pool

@contextmanager
def get_connection(db_path: str = None):
    """
    Get a connection from the pool.
    
    This context manager acquires a connection from the pool and
    returns it to the pool when the context is exited.
    
    Args:
        db_path: Path to the SQLite database (required on first call)
        
    Returns:
        A database connection
        
    Raises:
        ValueError: If db_path is not provided on first call
    """
    pool = get_connection_pool(db_path)
    with pool.get_connection() as conn:
        yield conn
