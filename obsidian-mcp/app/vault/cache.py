"""
Simple LRU cache for vault operations
"""
import logging
import time
import threading
from typing import Any, Optional, Dict
from collections import OrderedDict

logger = logging.getLogger(__name__)


class SimpleCache:
    """Simple LRU cache with TTL support (thread-safe)"""

    def __init__(self, max_size: int = 1000, default_ttl: int = 300):
        """
        Initialize cache

        Args:
            max_size: Maximum number of items in cache
            default_ttl: Default TTL in seconds
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict[str, tuple[Any, float]] = OrderedDict()
        self._hits = 0
        self._misses = 0
        self._lock = threading.Lock()  # Thread safety

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None

            value, expiry = self._cache[key]

            # Check if expired
            if expiry > 0 and time.time() > expiry:
                del self._cache[key]
                self._misses += 1
                return None

            # Move to end (mark as recently used)
            self._cache.move_to_end(key)
            self._hits += 1
            return value

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache
            ttl: TTL in seconds (None = default, 0 = no expiry)
        """
        if ttl is None:
            ttl = self.default_ttl

        expiry = time.time() + ttl if ttl > 0 else 0

        with self._lock:
            # Update existing key or add new
            if key in self._cache:
                self._cache[key] = (value, expiry)
                self._cache.move_to_end(key)
            else:
                self._cache[key] = (value, expiry)

                # Evict oldest if at capacity
                if len(self._cache) > self.max_size:
                    oldest_key = next(iter(self._cache))
                    del self._cache[oldest_key]
                    logger.debug(f"Evicted cache key: {oldest_key}")

    def delete(self, key: str):
        """Delete key from cache"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def invalidate_pattern(self, pattern: str):
        """
        Invalidate all keys matching pattern

        Args:
            pattern: Pattern to match (simple prefix matching)
        """
        with self._lock:
            keys_to_delete = [k for k in self._cache.keys() if k.startswith(pattern)]
            for key in keys_to_delete:
                del self._cache[key]
            logger.debug(f"Invalidated {len(keys_to_delete)} cache keys matching '{pattern}'")

    def clear(self):
        """Clear all cache"""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Dict with cache stats
        """
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0

            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "hits": self._hits,
                "misses": self._misses,
                "hit_rate_percent": round(hit_rate, 2)
            }
