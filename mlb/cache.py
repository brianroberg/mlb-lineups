"""Request caching and rate limiting for MLB API calls."""

import functools
import hashlib
import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any, Callable

logger = logging.getLogger(__name__)

# Cache TTL configuration based on game status
TTL_CONFIG: dict[str, int] = {
    'Pre-Game': 300,       # 5 minutes - lineups may change
    'Warmup': 300,         # 5 minutes
    'Scheduled': 300,      # 5 minutes
    'In Progress': 60,     # 1 minute - live updates needed
    'Final': 3600,         # 1 hour - historical data
    'Game Over': 3600,     # 1 hour
    'Postponed': 1800,     # 30 minutes
    'Suspended': 1800,     # 30 minutes
    'Cancelled': 1800,     # 30 minutes
    'default': 300,        # 5 minutes default
}

# Rate limiter configuration
RATE_LIMIT_CAPACITY = 100      # Max tokens (burst size)
RATE_LIMIT_REFILL_RATE = 10.0  # Tokens per second


@dataclass
class CacheEntry:
    """Cached API response with expiration timestamp."""

    value: Any
    expiration: float

    def is_expired(self) -> bool:
        """Check if this cache entry has expired."""
        return time.time() > self.expiration


class CacheManager:
    """Thread-safe in-memory cache with TTL support."""

    def __init__(self, max_entries: int = 10000):
        """
        Initialize cache manager.

        Args:
            max_entries: Maximum number of entries before eviction
        """
        self._cache: dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._max_entries = max_entries
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get cached value if not expired.

        Args:
            key: Cache key
            default: Value to return if key not found/expired

        Returns:
            Cached value or default if not found/expired
        """
        with self._lock:
            if key in self._cache:
                entry = self._cache[key]
                if not entry.is_expired():
                    self._stats['hits'] += 1
                    return entry.value
                # Remove expired entry
                del self._cache[key]

            self._stats['misses'] += 1
            return default

    def set(self, key: str, value: Any, ttl: int) -> None:
        """
        Store value in cache with TTL.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds
        """
        with self._lock:
            # Evict if at capacity
            if len(self._cache) >= self._max_entries:
                self._evict_oldest()

            expiration = time.time() + ttl
            self._cache[key] = CacheEntry(value=value, expiration=expiration)

    def invalidate(self, key: str) -> bool:
        """
        Remove a specific key from cache.

        Args:
            key: Cache key to remove

        Returns:
            True if key was found and removed
        """
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                return True
            return False

    def clear(self) -> None:
        """Clear all cached entries."""
        with self._lock:
            self._cache.clear()
            logger.info("Cache cleared")

    def get_stats(self) -> dict[str, int]:
        """
        Get cache statistics.

        Returns:
            Dict with hits, misses, evictions, and size
        """
        with self._lock:
            return {
                **self._stats,
                'size': len(self._cache),
            }

    def _evict_oldest(self) -> None:
        """Evict oldest 10% of entries when at capacity."""
        to_remove = max(1, int(self._max_entries * 0.1))
        sorted_items = sorted(
            self._cache.items(),
            key=lambda x: x[1].expiration
        )
        for key, _ in sorted_items[:to_remove]:
            del self._cache[key]
            self._stats['evictions'] += 1


class RateLimiter:
    """Token bucket rate limiter for API calls."""

    def __init__(self, capacity: int, refill_rate: float):
        """
        Initialize rate limiter.

        Args:
            capacity: Maximum tokens (allows bursts up to this size)
            refill_rate: Tokens added per second
        """
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens = float(capacity)
        self._last_refill = time.time()
        self._lock = threading.Lock()
        self._stats = {'acquired': 0, 'waited': 0}

    def acquire(self, timeout: float = 30.0) -> bool:
        """
        Acquire a token, waiting if necessary.

        Args:
            timeout: Maximum time to wait for a token

        Returns:
            True if token acquired, False if timeout
        """
        start = time.time()
        waited = False

        while True:
            with self._lock:
                self._refill()
                if self._tokens >= 1.0:
                    self._tokens -= 1.0
                    self._stats['acquired'] += 1
                    if waited:
                        self._stats['waited'] += 1
                    return True

            # Check timeout after lock release
            elapsed = time.time() - start
            if elapsed >= timeout:
                logger.warning("Rate limiter timeout exceeded")
                return False

            # Wait a bit before retrying (outside of lock)
            time.sleep(0.1)
            waited = True

    def get_stats(self) -> dict[str, Any]:
        """
        Get rate limiter statistics.

        Returns:
            Dict with tokens, acquired count, and waited count
        """
        with self._lock:
            self._refill()
            return {
                'tokens_available': round(self._tokens, 2),
                'capacity': self.capacity,
                'refill_rate': self.refill_rate,
                **self._stats,
            }

    def _refill(self) -> None:
        """Add tokens based on time elapsed."""
        now = time.time()
        elapsed = now - self._last_refill
        tokens_to_add = elapsed * self.refill_rate
        self._tokens = min(self.capacity, self._tokens + tokens_to_add)
        self._last_refill = now


def get_ttl_for_game_status(status: str | None) -> int:
    """
    Determine cache TTL based on game status.

    Args:
        status: Game status string from MLB API

    Returns:
        TTL in seconds
    """
    if status is None:
        return TTL_CONFIG['default']
    return TTL_CONFIG.get(status, TTL_CONFIG['default'])


def generate_cache_key(func_name: str, args: tuple, kwargs: dict) -> str:
    """
    Generate consistent cache key from function call.

    Args:
        func_name: Name of the function
        args: Positional arguments
        kwargs: Keyword arguments

    Returns:
        Hash-based cache key
    """
    # For simple cases, use direct string representation
    if not kwargs and all(isinstance(a, (str, int, type(None))) for a in args):
        args_str = ':'.join(str(a) if a is not None else 'None' for a in args)
        return f"{func_name}:{args_str}"

    # For complex arguments, use hash
    key_data = {
        'func': func_name,
        'args': [str(a) for a in args],
        'kwargs': {k: str(v) for k, v in sorted(kwargs.items())},
    }
    key_str = json.dumps(key_data, sort_keys=True)
    key_hash = hashlib.sha256(key_str.encode()).hexdigest()[:16]
    return f"{func_name}:{key_hash}"


_CACHE_SENTINEL = object()  # Sentinel to distinguish cache miss from cached None


def cached(ttl_func: Callable[..., int] | int = 300) -> Callable:
    """
    Decorator for caching function results.

    Args:
        ttl_func: Either a fixed TTL in seconds, or a callable that takes
                  the same arguments as the decorated function and returns TTL

    Returns:
        Decorator function

    Example:
        @cached(300)  # Fixed 5 minute TTL
        def my_function(x): ...

        @cached(lambda game_id, status: get_ttl_for_game_status(status))
        def get_game_data(game_id, status): ...
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            # Generate cache key
            cache_key = generate_cache_key(func.__name__, args, kwargs)

            # Check cache
            cached_value = cache_manager.get(cache_key, default=_CACHE_SENTINEL)
            if cached_value is not _CACHE_SENTINEL:
                logger.debug(f"Cache hit: {func.__name__}")
                return cached_value

            # Execute function
            logger.debug(f"Cache miss: {func.__name__}")
            result = func(*args, **kwargs)

            # Determine TTL
            if callable(ttl_func):
                try:
                    ttl = ttl_func(*args, **kwargs)
                except Exception:
                    ttl = TTL_CONFIG['default']
            else:
                ttl = ttl_func

            # Cache result
            try:
                cache_manager.set(cache_key, result, ttl)
            except Exception as e:
                logger.warning(f"Cache set failed: {e}")

            return result

        return wrapper
    return decorator


# Module-level singleton instances
cache_manager = CacheManager()
rate_limiter = RateLimiter(
    capacity=RATE_LIMIT_CAPACITY,
    refill_rate=RATE_LIMIT_REFILL_RATE
)


def clear_cache() -> None:
    """Clear the global cache. Useful for testing."""
    cache_manager.clear()
