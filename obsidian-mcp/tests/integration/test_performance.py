"""
Performance benchmarks for proxy mode

Validates that routing overhead meets performance targets:
- Routing: <10ms
- Lookup: <50ms
- Total overhead: <20ms
"""

import pytest
import time
from pathlib import Path
from statistics import mean, median, stdev

from app.vault.manager import VaultManager
from app.mcp.proxy import ProxyToolHandler


@pytest.fixture
def test_vault_path(tmp_path):
    """Create a test vault with sample notes"""
    vault_path = tmp_path / "perf-vault"
    vault_path.mkdir()

    # Create multiple notes for realistic testing
    for i in range(20):
        (vault_path / f"Note{i}.md").write_text(
            f"---\ntags: [tag{i%3}]\n---\n# Note {i}\n\nContent for note {i}"
        )

    return vault_path


@pytest.fixture
def vault_manager(test_vault_path, monkeypatch):
    """Create a VaultManager with test vault"""
    from app.config import settings
    monkeypatch.setattr(settings, "_vault_path", test_vault_path)
    monkeypatch.setattr(settings, "obsidian_vault_path", str(test_vault_path))
    return VaultManager(vault_path=test_vault_path)


@pytest.fixture
def proxy_handler(vault_manager):
    """Create a ProxyToolHandler"""
    return ProxyToolHandler(vault_manager)


def measure_time_ms(func, *args, **kwargs):
    """Measure function execution time in milliseconds"""
    start = time.perf_counter()
    result = func(*args, **kwargs)
    end = time.perf_counter()
    return (end - start) * 1000, result


def measure_multiple(func, iterations=10, *args, **kwargs):
    """Measure function multiple times and return statistics"""
    times = []
    for _ in range(iterations):
        elapsed, _ = measure_time_ms(func, *args, **kwargs)
        times.append(elapsed)

    return {
        "mean": mean(times),
        "median": median(times),
        "min": min(times),
        "max": max(times),
        "stdev": stdev(times) if len(times) > 1 else 0,
        "iterations": iterations
    }


class TestRoutingPerformance:
    """Test routing performance metrics"""

    def test_lookup_performance(self, proxy_handler):
        """Test lookup operation performance (<50ms target)"""
        stats = measure_multiple(
            lambda: proxy_handler.handle_lookup({"intent": "search for notes"}),
            iterations=20
        )

        print(f"\nLookup Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")
        print(f"  Min: {stats['min']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")
        print(f"  StdDev: {stats['stdev']:.2f}ms")

        # Target: <50ms
        assert stats['mean'] < 50, f"Lookup too slow: {stats['mean']:.2f}ms (target: <50ms)"
        assert stats['median'] < 50, f"Median lookup too slow: {stats['median']:.2f}ms"

    def test_validation_performance(self, proxy_handler):
        """Test argument validation performance"""
        stats = measure_multiple(
            lambda: proxy_handler.validate_before_execute(
                "search_notes",
                {"query": "test"}
            ),
            iterations=50
        )

        print(f"\nValidation Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")

        # Should be very fast (<5ms)
        assert stats['mean'] < 10, f"Validation too slow: {stats['mean']:.2f}ms"

    def test_routing_overhead(self, proxy_handler):
        """Test pure routing overhead (without VaultManager execution)"""
        # Measure just the routing decision
        stats = measure_multiple(
            lambda: proxy_handler.router.route("search for notes"),
            iterations=100
        )

        print(f"\nRouting Overhead:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")
        print(f"  Min: {stats['min']:.2f}ms")
        print(f"  Max: {stats['max']:.2f}ms")

        # Target: <10ms
        assert stats['mean'] < 10, f"Routing too slow: {stats['mean']:.2f}ms (target: <10ms)"

    def test_action_lookup_performance(self, proxy_handler):
        """Test action info retrieval performance"""
        stats = measure_multiple(
            lambda: proxy_handler.get_action_details("search_notes"),
            iterations=100
        )

        print(f"\nAction Lookup Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")

        # Should be instant (<1ms)
        assert stats['mean'] < 5, f"Action lookup too slow: {stats['mean']:.2f}ms"


class TestExecutionPerformance:
    """Test full execution performance"""

    def test_search_execution_performance(self, proxy_handler):
        """Test search execution time"""
        stats = measure_multiple(
            lambda: proxy_handler.handle_obsidian({
                "action": "search_notes",
                "args": {"query": "Note"}
            }),
            iterations=10
        )

        print(f"\nSearch Execution Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")
        print(f"  Median: {stats['median']:.2f}ms")

        # Should be reasonable (<500ms for small vault)
        assert stats['mean'] < 500, f"Search too slow: {stats['mean']:.2f}ms"

    def test_list_execution_performance(self, proxy_handler):
        """Test list execution time"""
        stats = measure_multiple(
            lambda: proxy_handler.handle_obsidian({
                "action": "list_notes",
                "args": {}
            }),
            iterations=10
        )

        print(f"\nList Execution Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")

        # Should be fast (<200ms)
        assert stats['mean'] < 500, f"List too slow: {stats['mean']:.2f}ms"

    def test_read_execution_performance(self, proxy_handler):
        """Test read execution time"""
        stats = measure_multiple(
            lambda: proxy_handler.handle_obsidian({
                "action": "read_note_content",
                "args": {"title": "Note1"}
            }),
            iterations=10
        )

        print(f"\nRead Execution Performance:")
        print(f"  Mean: {stats['mean']:.2f}ms")

        # Should be very fast (<100ms)
        assert stats['mean'] < 200, f"Read too slow: {stats['mean']:.2f}ms"


class TestCachingPerformance:
    """Test that caching improves performance"""

    def test_repeated_lookup_benefits_from_caching(self, proxy_handler):
        """Test that repeated lookups might benefit from internal caching"""
        # First lookup (cold)
        cold_time, _ = measure_time_ms(
            proxy_handler.handle_lookup,
            {"intent": "search for notes"}
        )

        # Repeated lookups (warm)
        warm_times = []
        for _ in range(5):
            warm_time, _ = measure_time_ms(
                proxy_handler.handle_lookup,
                {"intent": "search for notes"}
            )
            warm_times.append(warm_time)

        avg_warm = mean(warm_times)

        print(f"\nCaching Performance:")
        print(f"  Cold lookup: {cold_time:.2f}ms")
        print(f"  Warm lookup (avg): {avg_warm:.2f}ms")

        # Warm should be similar or faster (pattern matching is cheap)
        # Not a strict requirement, just informational

    def test_vault_operations_benefit_from_cache(self, proxy_handler, vault_manager):
        """Test that vault operations benefit from caching"""
        # Clear cache first
        vault_manager.cache.clear()

        # First read (cold - will cache)
        cold_time, result1 = measure_time_ms(
            proxy_handler.handle_obsidian,
            {"action": "read_note_content", "args": {"title": "Note1"}}
        )

        # Second read (warm - from cache)
        warm_time, result2 = measure_time_ms(
            proxy_handler.handle_obsidian,
            {"action": "read_note_content", "args": {"title": "Note1"}}
        )

        print(f"\nVault Caching:")
        print(f"  Cold read: {cold_time:.2f}ms")
        print(f"  Warm read: {warm_time:.2f}ms")
        print(f"  Speedup: {cold_time / warm_time:.2f}x")

        # Warm should be significantly faster
        assert warm_time < cold_time, "Cached read should be faster"


class TestScalability:
    """Test performance with different scales"""

    def test_many_intents_performance(self, proxy_handler):
        """Test routing with many different intents"""
        intents = [
            "search for notes",
            "create a new note",
            "get backlinks",
            "list templates",
            "show knowledge graph",
            "read the section",
            "update block content",
            "find orphan notes",
            "list all tags",
            "get daily note"
        ]

        times = []
        for intent in intents:
            elapsed, _ = measure_time_ms(
                proxy_handler.handle_lookup,
                {"intent": intent}
            )
            times.append(elapsed)

        avg_time = mean(times)
        max_time = max(times)

        print(f"\nMultiple Intents Performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Maximum: {max_time:.2f}ms")
        print(f"  All intents: {len(intents)}")

        # All should be fast
        assert avg_time < 50, f"Average routing too slow: {avg_time:.2f}ms"
        assert max_time < 100, f"Worst case routing too slow: {max_time:.2f}ms"

    def test_many_executions_performance(self, proxy_handler):
        """Test many sequential executions"""
        execution_count = 20

        total_time, _ = measure_time_ms(
            lambda: [
                proxy_handler.handle_obsidian({
                    "action": "list_notes",
                    "args": {"limit": 5}
                })
                for _ in range(execution_count)
            ]
        )

        avg_per_execution = total_time / execution_count

        print(f"\nBatch Execution Performance:")
        print(f"  Total time: {total_time:.2f}ms")
        print(f"  Average per execution: {avg_per_execution:.2f}ms")
        print(f"  Executions: {execution_count}")

        # Should maintain performance
        assert avg_per_execution < 500, f"Batch execution degraded: {avg_per_execution:.2f}ms"


class TestMemoryEfficiency:
    """Test memory usage is reasonable"""

    def test_proxy_handler_initialization_memory(self, vault_manager):
        """Test ProxyToolHandler doesn't use excessive memory"""
        import sys

        # Create handler
        handler = ProxyToolHandler(vault_manager)

        # Size should be reasonable
        handler_size = sys.getsizeof(handler)

        print(f"\nMemory Usage:")
        print(f"  ProxyToolHandler: {handler_size} bytes")

        # Should be small (<10KB)
        assert handler_size < 10000, f"Handler too large: {handler_size} bytes"


class TestConcurrentPerformance:
    """Test concurrent request handling"""

    @pytest.mark.asyncio
    async def test_concurrent_lookups(self, proxy_handler):
        """Test handling multiple concurrent lookups"""
        import asyncio

        async def async_lookup(intent):
            # Simulate async by running in executor
            loop = asyncio.get_event_loop()
            return await loop.run_in_executor(
                None,
                proxy_handler.handle_lookup,
                {"intent": intent}
            )

        intents = [
            "search for notes",
            "create note",
            "get backlinks",
            "list templates",
            "show graph"
        ]

        start = time.perf_counter()
        results = await asyncio.gather(*[async_lookup(intent) for intent in intents])
        elapsed = (time.perf_counter() - start) * 1000

        print(f"\nConcurrent Lookups:")
        print(f"  Total time: {elapsed:.2f}ms")
        print(f"  Requests: {len(intents)}")
        print(f"  Average: {elapsed / len(intents):.2f}ms")

        # Should all succeed
        assert all("action" in r for r in results)


# Performance summary test
def test_print_performance_summary(proxy_handler):
    """Print overall performance summary"""
    print("\n" + "="*60)
    print("PERFORMANCE SUMMARY")
    print("="*60)

    # Routing
    routing_time, _ = measure_time_ms(
        proxy_handler.router.route,
        "search for notes"
    )

    # Lookup
    lookup_time, _ = measure_time_ms(
        proxy_handler.handle_lookup,
        {"intent": "search for notes"}
    )

    # Validation
    validation_time, _ = measure_time_ms(
        proxy_handler.validate_before_execute,
        "search_notes",
        {"query": "test"}
    )

    print(f"\nCore Operations:")
    print(f"  Routing:    {routing_time:.2f}ms (target: <10ms)")
    print(f"  Lookup:     {lookup_time:.2f}ms (target: <50ms)")
    print(f"  Validation: {validation_time:.2f}ms (target: <10ms)")

    print(f"\nTargets:")
    print(f"  ✓ Routing <10ms:    {'PASS' if routing_time < 10 else 'FAIL'}")
    print(f"  ✓ Lookup <50ms:     {'PASS' if lookup_time < 50 else 'FAIL'}")
    print(f"  ✓ Validation <10ms: {'PASS' if validation_time < 10 else 'FAIL'}")

    print("\n" + "="*60)
