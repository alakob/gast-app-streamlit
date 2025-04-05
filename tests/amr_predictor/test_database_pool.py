"""Tests for the Database Connection Pool."""

import pytest
import concurrent.futures
import threading
import time
import sqlite3

from amr_predictor.bakta.database_pool import ConnectionPool, get_connection_pool, get_connection


def test_connection_pool_initialization(temp_db_path):
    """Test initializing a connection pool."""
    pool = ConnectionPool(
        db_path=temp_db_path,
        min_connections=2,
        max_connections=5
    )
    
    # Verify pool was initialized with minimum connections
    assert len(pool.pool) == 2
    assert len(pool.in_use) == 0
    
    # Clean up
    pool.close_all()


def test_get_connection_from_pool(temp_db_path):
    """Test getting a connection from the pool."""
    pool = ConnectionPool(
        db_path=temp_db_path,
        min_connections=2,
        max_connections=5
    )
    
    # Get a connection using context manager
    with pool.get_connection() as conn:
        # Verify connection is valid
        assert isinstance(conn, sqlite3.Connection)
        
        # Verify connection is in use
        assert len(pool.in_use) == 1
        assert threading.get_ident() in pool.in_use
        
        # Execute a query to verify connection works
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        assert result[0] == 1
    
    # Verify connection was returned to the pool
    assert len(pool.in_use) == 0
    assert len(pool.pool) == 2
    
    # Clean up
    pool.close_all()


def test_reuse_connection(temp_db_path):
    """Test that connections are reused."""
    pool = ConnectionPool(
        db_path=temp_db_path,
        min_connections=1,
        max_connections=5
    )
    
    # Take the only connection from the pool
    with pool.get_connection() as conn1:
        # Verify pool is empty
        assert len(pool.pool) == 0
    
    # Verify connection was returned to the pool
    assert len(pool.pool) == 1
    
    # Get another connection, which should be the same one
    with pool.get_connection() as conn2:
        # Can't directly compare connection objects, but we can test that
        # the pool is empty again, indicating reuse
        assert len(pool.pool) == 0
    
    # Clean up
    pool.close_all()


def test_max_connections(temp_db_path):
    """Test that the pool respects max connections."""
    max_conns = 3
    pool = ConnectionPool(
        db_path=temp_db_path,
        min_connections=1,
        max_connections=max_conns
    )
    
    # Store connections to keep them in use
    connections = []
    
    # Acquire max_conns connections
    for _ in range(max_conns):
        conn = pool._acquire_connection()
        connections.append(conn)
    
    # Verify all connections are in use
    assert len(pool.in_use) == max_conns
    assert len(pool.pool) == 0
    
    # Release all connections
    for conn in connections:
        thread_id = threading.get_ident()
        pool._release_connection(thread_id, conn)
    
    # Clean up
    pool.close_all()


def test_connection_isolation(temp_db_path):
    """Test that connections provide isolation."""
    pool = ConnectionPool(
        db_path=temp_db_path,
        min_connections=2,
        max_connections=5
    )
    
    # Create a test table
    with pool.get_connection() as conn:
        conn.execute("CREATE TABLE test (id INTEGER PRIMARY KEY, value TEXT)")
        conn.commit()
    
    # In one connection, insert a row but don't commit
    with pool.get_connection() as conn1:
        conn1.execute("INSERT INTO test (id, value) VALUES (1, 'test1')")
        
        # In another connection, the row shouldn't be visible
        with pool.get_connection() as conn2:
            cursor = conn2.cursor()
            cursor.execute("SELECT COUNT(*) FROM test")
            count = cursor.fetchone()[0]
            assert count == 0
        
        # Commit the first connection
        conn1.commit()
    
    # Now the row should be visible in a new connection
    with pool.get_connection() as conn3:
        cursor = conn3.cursor()
        cursor.execute("SELECT COUNT(*) FROM test")
        count = cursor.fetchone()[0]
        assert count == 1
    
    # Clean up
    pool.close_all()


def test_global_connection_pool(temp_db_path):
    """Test the global connection pool functions."""
    # Get the global connection pool
    pool1 = get_connection_pool(db_path=temp_db_path)
    
    # Get it again, should be the same instance
    pool2 = get_connection_pool()
    
    # Verify both references point to the same pool
    assert pool1 is pool2
    
    # Use the global get_connection function
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()[0]
        assert result == 1
    
    # Clean up
    pool1.close_all()


def test_concurrent_connections(temp_db_path):
    """Test concurrent connections with multiple threads."""
    pool = ConnectionPool(
        db_path=temp_db_path,
        min_connections=2,
        max_connections=10
    )
    
    # Create a test table
    with pool.get_connection() as conn:
        conn.execute("CREATE TABLE concurrent_test (id INTEGER PRIMARY KEY, thread_id INTEGER)")
        conn.commit()
    
    def worker_task(worker_id):
        """Task for each worker thread."""
        try:
            with pool.get_connection() as conn:
                # Insert a row with the worker's ID
                conn.execute(
                    "INSERT INTO concurrent_test (id, thread_id) VALUES (?, ?)",
                    (worker_id, threading.get_ident())
                )
                conn.commit()
                
                # Sleep briefly to simulate work
                time.sleep(0.05)
                
                # Verify our row exists
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT thread_id FROM concurrent_test WHERE id = ?",
                    (worker_id,)
                )
                result = cursor.fetchone()
                assert result is not None
                
                return True
        except Exception as e:
            print(f"Worker {worker_id} error: {str(e)}")
            return False
    
    # Run multiple worker threads concurrently
    num_workers = 8
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_workers) as executor:
        futures = [executor.submit(worker_task, i) for i in range(num_workers)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]
    
    # Verify all workers completed successfully
    assert all(results)
    
    # Verify all rows were inserted
    with pool.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM concurrent_test")
        count = cursor.fetchone()[0]
        assert count == num_workers
    
    # Clean up
    pool.close_all()
