"""Retry when Google is busy (503 high demand, 429 too many requests) instead of failing at once."""
import time

BUSY_WORDS = ("503", "429", "unavailable", "resource_exhausted", "high demand", "overloaded",
              "server disconnected", "timed out", "timeout")


def is_busy_error(err):
    text = f"{type(err).__name__} {err}".lower()
    return any(w in text for w in BUSY_WORDS)


def call_with_retry(fn, tries=3, delays=(1.0, 2.5)):
    """Run fn(). If Google is busy, wait a moment and try again. Other errors are raised straight away."""
    for i in range(tries):
        try:
            return fn()
        except Exception as err:
            if not is_busy_error(err) or i == tries - 1:
                raise
            time.sleep(delays[min(i, len(delays) - 1)])
