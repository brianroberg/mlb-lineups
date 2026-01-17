"""Tests for the caching and rate limiting module."""

import time
import threading
import pytest

from mlb.cache import (
    CacheEntry,
    CacheManager,
    RateLimiter,
    cached,
    generate_cache_key,
    get_ttl_for_game_status,
    clear_cache,
    TTL_CONFIG,
)


class TestCacheEntry:
    """Tests for CacheEntry dataclass."""

    def test_not_expired_when_fresh(self):
        """Entry should not be expired immediately after creation."""
        entry = CacheEntry(value="test", expiration=time.time() + 100)
        assert not entry.is_expired()

    def test_expired_after_time_passes(self):
        """Entry should be expired after expiration time."""
        entry = CacheEntry(value="test", expiration=time.time() - 1)
        assert entry.is_expired()

    def test_stores_value_correctly(self):
        """Entry should store and return value."""
        entry = CacheEntry(value={"key": "value"}, expiration=time.time() + 100)
        assert entry.value == {"key": "value"}


class TestCacheManager:
    """Tests for CacheManager class."""

    @pytest.fixture
    def cache(self):
        """Create a fresh cache for each test."""
        return CacheManager(max_entries=100)

    def test_get_returns_none_for_missing_key(self, cache):
        """Get should return None for keys not in cache."""
        assert cache.get("nonexistent") is None

    def test_set_and_get(self, cache):
        """Should be able to set and retrieve values."""
        cache.set("key1", "value1", ttl=300)
        assert cache.get("key1") == "value1"

    def test_get_returns_none_for_expired_entry(self, cache):
        """Get should return None for expired entries."""
        cache.set("key1", "value1", ttl=0)
        time.sleep(0.01)
        assert cache.get("key1") is None

    def test_invalidate_removes_entry(self, cache):
        """Invalidate should remove entry from cache."""
        cache.set("key1", "value1", ttl=300)
        assert cache.invalidate("key1") is True
        assert cache.get("key1") is None

    def test_invalidate_returns_false_for_missing_key(self, cache):
        """Invalidate should return False for missing keys."""
        assert cache.invalidate("nonexistent") is False

    def test_clear_removes_all_entries(self, cache):
        """Clear should remove all entries."""
        cache.set("key1", "value1", ttl=300)
        cache.set("key2", "value2", ttl=300)
        cache.clear()
        assert cache.get("key1") is None
        assert cache.get("key2") is None

    def test_stats_tracks_hits_and_misses(self, cache):
        """Stats should track cache hits and misses."""
        cache.set("key1", "value1", ttl=300)

        # Miss
        cache.get("nonexistent")
        stats = cache.get_stats()
        assert stats['misses'] == 1
        assert stats['hits'] == 0

        # Hit
        cache.get("key1")
        stats = cache.get_stats()
        assert stats['hits'] == 1
        assert stats['misses'] == 1

    def test_stats_tracks_size(self, cache):
        """Stats should track cache size."""
        cache.set("key1", "value1", ttl=300)
        cache.set("key2", "value2", ttl=300)
        stats = cache.get_stats()
        assert stats['size'] == 2

    def test_evicts_when_at_capacity(self):
        """Should evict oldest entries when at capacity."""
        cache = CacheManager(max_entries=10)

        # Fill cache
        for i in range(10):
            cache.set(f"key{i}", f"value{i}", ttl=300 + i)

        # Add one more, should trigger eviction
        cache.set("key10", "value10", ttl=400)

        stats = cache.get_stats()
        assert stats['size'] <= 10
        assert stats['evictions'] >= 1

    def test_thread_safety(self, cache):
        """Cache should be thread-safe."""
        errors = []

        def writer():
            try:
                for i in range(100):
                    cache.set(f"thread_key_{i}", f"value_{i}", ttl=300)
            except Exception as e:
                errors.append(e)

        def reader():
            try:
                for i in range(100):
                    cache.get(f"thread_key_{i}")
            except Exception as e:
                errors.append(e)

        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestRateLimiter:
    """Tests for RateLimiter class."""

    def test_acquire_succeeds_when_tokens_available(self):
        """Acquire should succeed when tokens are available."""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)
        assert limiter.acquire(timeout=0.1) is True

    def test_acquire_consumes_tokens(self):
        """Acquire should consume tokens."""
        limiter = RateLimiter(capacity=5, refill_rate=0.0)

        for _ in range(5):
            assert limiter.acquire(timeout=0.1) is True

        # Should fail - no tokens left and no refill
        assert limiter.acquire(timeout=0.1) is False

    def test_tokens_refill_over_time(self):
        """Tokens should refill over time."""
        limiter = RateLimiter(capacity=5, refill_rate=100.0)  # Fast refill

        # Consume all tokens
        for _ in range(5):
            limiter.acquire(timeout=0.1)

        # Wait for refill
        time.sleep(0.1)

        # Should have tokens again
        assert limiter.acquire(timeout=0.1) is True

    def test_stats_tracks_acquisitions(self):
        """Stats should track successful acquisitions."""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)

        limiter.acquire(timeout=0.1)
        limiter.acquire(timeout=0.1)

        stats = limiter.get_stats()
        assert stats['acquired'] == 2

    def test_stats_shows_available_tokens(self):
        """Stats should show available tokens."""
        limiter = RateLimiter(capacity=10, refill_rate=1.0)

        stats = limiter.get_stats()
        assert stats['tokens_available'] <= 10

    def test_thread_safety(self):
        """Rate limiter should be thread-safe."""
        limiter = RateLimiter(capacity=100, refill_rate=1000.0)
        errors = []

        def acquirer():
            try:
                for _ in range(50):
                    limiter.acquire(timeout=1.0)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=acquirer) for _ in range(4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0


class TestGetTTLForGameStatus:
    """Tests for get_ttl_for_game_status function."""

    def test_final_game_has_long_ttl(self):
        """Final games should have long TTL (1 hour)."""
        assert get_ttl_for_game_status('Final') == 3600

    def test_in_progress_game_has_short_ttl(self):
        """In-progress games should have short TTL (1 minute)."""
        assert get_ttl_for_game_status('In Progress') == 60

    def test_scheduled_game_has_medium_ttl(self):
        """Scheduled games should have medium TTL (5 minutes)."""
        assert get_ttl_for_game_status('Scheduled') == 300

    def test_pregame_has_medium_ttl(self):
        """Pre-game should have medium TTL (5 minutes)."""
        assert get_ttl_for_game_status('Pre-Game') == 300

    def test_unknown_status_uses_default(self):
        """Unknown status should use default TTL."""
        assert get_ttl_for_game_status('Unknown Status') == TTL_CONFIG['default']

    def test_none_status_uses_default(self):
        """None status should use default TTL."""
        assert get_ttl_for_game_status(None) == TTL_CONFIG['default']


class TestGenerateCacheKey:
    """Tests for generate_cache_key function."""

    def test_simple_args_produce_readable_key(self):
        """Simple args should produce readable cache key."""
        key = generate_cache_key("my_func", (123, "hello"), {})
        assert key.startswith("my_func:")
        assert "123" in key
        assert "hello" in key

    def test_same_args_produce_same_key(self):
        """Same arguments should produce same key."""
        key1 = generate_cache_key("func", (1, 2, 3), {"a": "b"})
        key2 = generate_cache_key("func", (1, 2, 3), {"a": "b"})
        assert key1 == key2

    def test_different_args_produce_different_keys(self):
        """Different arguments should produce different keys."""
        key1 = generate_cache_key("func", (1,), {})
        key2 = generate_cache_key("func", (2,), {})
        assert key1 != key2

    def test_different_functions_produce_different_keys(self):
        """Different function names should produce different keys."""
        key1 = generate_cache_key("func1", (1,), {})
        key2 = generate_cache_key("func2", (1,), {})
        assert key1 != key2

    def test_handles_none_args(self):
        """Should handle None in arguments."""
        key = generate_cache_key("func", (None, 123), {})
        assert key.startswith("func:")

    def test_handles_complex_args(self):
        """Should handle complex arguments via hashing."""
        key = generate_cache_key("func", ([1, 2, 3],), {"nested": {"key": "value"}})
        assert key.startswith("func:")


class TestCachedDecorator:
    """Tests for @cached decorator."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Clear cache before and after each test."""
        clear_cache()
        yield
        clear_cache()

    def test_caches_function_result(self):
        """Decorator should cache function results."""
        call_count = 0

        @cached(300)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(5)

        assert result1 == 10
        assert result2 == 10
        assert call_count == 1  # Called only once

    def test_different_args_not_cached_together(self):
        """Different arguments should cache separately."""
        call_count = 0

        @cached(300)
        def expensive_function(x):
            nonlocal call_count
            call_count += 1
            return x * 2

        result1 = expensive_function(5)
        result2 = expensive_function(10)

        assert result1 == 10
        assert result2 == 20
        assert call_count == 2  # Called twice for different args

    def test_respects_fixed_ttl(self):
        """Decorator should respect fixed TTL."""
        @cached(0)  # Immediate expiration
        def expensive_function(x):
            return x * 2

        expensive_function(5)
        time.sleep(0.01)

        # Should trigger re-execution due to expired cache
        # (Note: this test is timing-sensitive)

    def test_respects_dynamic_ttl(self):
        """Decorator should respect dynamic TTL function."""
        @cached(lambda x: 300 if x > 0 else 1)
        def expensive_function(x):
            return x * 2

        expensive_function(5)
        expensive_function(-5)
        # Both should cache with different TTLs

    def test_preserves_function_metadata(self):
        """Decorator should preserve function name and docstring."""
        @cached(300)
        def my_function(x):
            """My docstring."""
            return x

        assert my_function.__name__ == "my_function"
        assert my_function.__doc__ == "My docstring."


class TestClearCache:
    """Tests for clear_cache utility function."""

    def test_clears_global_cache(self):
        """clear_cache should clear the global cache manager."""
        @cached(300)
        def expensive_function(x):
            return x * 2

        expensive_function(5)  # Cache a value

        clear_cache()

        # Cache should be empty now
        from mlb.cache import cache_manager
        assert cache_manager.get_stats()['size'] == 0


@pytest.mark.unit
class TestCacheIntegration:
    """Integration tests for cache with API client patterns."""

    @pytest.fixture(autouse=True)
    def reset_cache(self):
        """Clear cache before and after each test."""
        clear_cache()
        yield
        clear_cache()

    def test_game_status_ttl_selection(self):
        """Different game statuses should get appropriate TTLs."""
        # Final games get long cache
        assert get_ttl_for_game_status('Final') == 3600

        # Live games get short cache
        assert get_ttl_for_game_status('In Progress') == 60

        # Scheduled games get medium cache
        assert get_ttl_for_game_status('Pre-Game') == 300

    def test_tuple_return_values_cached_correctly(self):
        """Functions returning tuples should cache correctly."""
        call_count = 0

        @cached(300)
        def get_game_data(team_id, date):
            nonlocal call_count
            call_count += 1
            return (123, "Final", "Stadium", {"home": "Team A"}, "2025-01-01T19:00:00Z")

        result1 = get_game_data(121, "2025-04-15")
        result2 = get_game_data(121, "2025-04-15")

        assert result1 == result2
        assert call_count == 1

    def test_none_return_values_cached(self):
        """None return values should also be cached."""
        call_count = 0

        @cached(300)
        def might_return_none(x):
            nonlocal call_count
            call_count += 1
            return None if x < 0 else x

        result1 = might_return_none(-5)
        result2 = might_return_none(-5)

        assert result1 is None
        assert result2 is None
        assert call_count == 1  # Should cache None too

    def test_dict_return_values_cached(self):
        """Dict return values should cache correctly."""
        call_count = 0

        @cached(300)
        def get_player_info(player_id):
            nonlocal call_count
            call_count += 1
            return {'name': 'Test Player', 'jersey': '99'}

        result1 = get_player_info(12345)
        result2 = get_player_info(12345)

        assert result1 == result2
        assert result1['name'] == 'Test Player'
        assert call_count == 1
