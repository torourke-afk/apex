"""Per-session cache hit/miss counters.

Tracks calls vs. misses for every ``load_*`` Streamlit-cached wrapper so that
hit/miss ratio can be logged in debug mode.

Usage in a load_* wrapper
--------------------------
The ``@st.cache_data`` decorator bypasses the function body on a cache hit, so
logging inside the body only fires on misses.  The pattern here is:

1. ``record_call(name)`` — called by the **outer** (non-cached) function on
   every invocation (hit + miss).
2. ``record_miss(name)`` — called **inside** the ``@st.cache_data`` body, which
   only executes on a cache miss.
3. Hits are derived: hits = total_calls - misses.

Example::

    def load_product_pipeline(stage=None):
        cache_metrics.record_call("load_product_pipeline")
        return _load_product_pipeline_cached(stage)

    @st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
    def _load_product_pipeline_cached(stage=None):
        cache_metrics.record_miss("load_product_pipeline")
        return get_product_pipeline(stage=stage)

Logging
-------
Call ``log_hit_miss_ratio()`` at the end of each page render when
``APEX_DEBUG_MODE`` is enabled.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_lock = threading.Lock()
_calls: dict[str, int] = {}
_misses: dict[str, int] = {}


def record_call(name: str) -> None:
    """Increment total-call counter for *name*."""
    with _lock:
        _calls[name] = _calls.get(name, 0) + 1


def record_miss(name: str) -> None:
    """Increment miss counter for *name* (called inside cached body)."""
    with _lock:
        _misses[name] = _misses.get(name, 0) + 1
    logger.debug("cache miss: %s", name)


def get_stats() -> dict[str, dict]:
    """Return hit/miss stats keyed by function name."""
    with _lock:
        keys = sorted(set(list(_calls.keys()) + list(_misses.keys())))
        stats: dict[str, dict] = {}
        for k in keys:
            total = _calls.get(k, 0)
            misses = _misses.get(k, 0)
            hits = max(total - misses, 0)
            stats[k] = {
                "calls": total,
                "hits": hits,
                "misses": misses,
                "hit_ratio": hits / total if total > 0 else 0.0,
            }
        return stats


def log_hit_miss_ratio() -> None:
    """Log hit/miss ratio for all tracked functions (debug mode only)."""
    stats = get_stats()
    if not stats:
        return
    for name, s in stats.items():
        logger.info(
            "cache_metrics | %s — calls=%d hits=%d misses=%d ratio=%.2f",
            name,
            s["calls"],
            s["hits"],
            s["misses"],
            s["hit_ratio"],
        )


def reset() -> None:
    """Reset all counters (useful for test isolation)."""
    with _lock:
        _calls.clear()
        _misses.clear()
