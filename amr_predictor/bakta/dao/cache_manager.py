#!/usr/bin/env python3
"""
Cache manager for Bakta data entities.

This module provides a cache implementation to optimize access to frequently
queried data from the Bakta database.
"""

import logging
import time
from typing import Dict, List, Any, Optional, Union, Generic, TypeVar, Callable
from functools import wraps
from threading import RLock
from datetime import datetime, timedelta

logger = logging.getLogger("bakta-cache")

# Generic type for cached items
T = TypeVar('T')

class CacheItem(Generic[T]):
    """Container for cached items with expiration tracking."""
    
    def __init__(self, value: T, ttl_seconds: int = 300):
        """
        Initialize a cache item.
        
        Args:
            value: The value to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        self.value = value
        self.expiry = time.time() + ttl_seconds
    
    def is_expired(self) -> bool:
        """Check if the cache item has expired."""
        return time.time() > self.expiry


class CacheManager:
    """
    Cache manager for Bakta data.
    
    This class provides a simple in-memory cache with expiration
    for optimizing frequent data access patterns.
    """
    
    def __init__(self, max_size: int = 1000):
        """
        Initialize the cache manager.
        
        Args:
            max_size: Maximum number of items to keep in cache
        """
        self._cache: Dict[str, CacheItem] = {}
        self._max_size = max_size
        self._lock = RLock()
        logger.info(f"Initialized cache manager with max size: {max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value or None if not found or expired
        """
        with self._lock:
            item = self._cache.get(key)
            if item is None:
                return None
            
            if item.is_expired():
                del self._cache[key]
                return None
            
            return item.value
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300) -> None:
        """
        Set a value in the cache.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl_seconds: Time to live in seconds (default: 5 minutes)
        """
        with self._lock:
            # Enforce cache size limit by removing oldest items if needed
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_oldest()
            
            self._cache[key] = CacheItem(value, ttl_seconds)
    
    def delete(self, key: str) -> None:
        """
        Delete a value from the cache.
        
        Args:
            key: Cache key
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
    
    def clear(self) -> None:
        """Clear all items from the cache."""
        with self._lock:
            self._cache.clear()
    
    def _evict_oldest(self) -> None:
        """Evict the oldest items from the cache to maintain size limits."""
        # Find expired items first
        expired_keys = [k for k, v in self._cache.items() if v.is_expired()]
        
        # Delete expired items
        for key in expired_keys:
            del self._cache[key]
        
        # If we still need to free up space, remove oldest items
        if len(self._cache) >= self._max_size:
            # Sort by expiry time and remove oldest 10% of items
            items = sorted(self._cache.items(), key=lambda x: x[1].expiry)
            to_remove = max(1, int(len(items) * 0.1))
            
            for i in range(to_remove):
                key, _ = items[i]
                del self._cache[key]
    
    def size(self) -> int:
        """Get the current number of items in the cache."""
        with self._lock:
            return len(self._cache)
    
    def stats(self) -> Dict[str, Any]:
        """Get statistics about the cache."""
        with self._lock:
            expired = sum(1 for item in self._cache.values() if item.is_expired())
            return {
                "total_items": len(self._cache),
                "expired_items": expired,
                "active_items": len(self._cache) - expired,
                "max_size": self._max_size,
                "usage_percent": (len(self._cache) / self._max_size) * 100 if self._max_size > 0 else 0
            }


# Global cache instance for application-wide use
global_cache = CacheManager()


def cached(ttl_seconds: int = 300, key_prefix: str = ""):
    """
    Decorator to cache function results.
    
    Args:
        ttl_seconds: Time to live in seconds (default: 5 minutes)
        key_prefix: Prefix for cache keys
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Generate cache key from function name and arguments
            key_parts = [key_prefix, func.__name__]
            
            # Add positional args to key
            for arg in args:
                key_parts.append(str(arg))
            
            # Add keyword args to key (sorted for consistency)
            for k, v in sorted(kwargs.items()):
                key_parts.append(f"{k}:{v}")
            
            cache_key = ":".join(key_parts)
            
            # Try to get from cache
            result = global_cache.get(cache_key)
            if result is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return result
            
            # Not in cache, call the function
            logger.debug(f"Cache miss for key: {cache_key}")
            result = func(*args, **kwargs)
            
            # Cache the result
            global_cache.set(cache_key, result, ttl_seconds)
            return result
        
        return wrapper
    
    return decorator


def invalidate_cache(pattern: str) -> int:
    """
    Invalidate cache entries matching a pattern.
    
    Args:
        pattern: String pattern to match against cache keys
        
    Returns:
        Number of invalidated cache entries
    """
    count = 0
    with global_cache._lock:
        keys_to_delete = [k for k in global_cache._cache.keys() if pattern in k]
        for key in keys_to_delete:
            del global_cache._cache[key]
            count += 1
    
    logger.info(f"Invalidated {count} cache entries matching pattern: {pattern}")
    return count 