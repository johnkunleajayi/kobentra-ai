"""A per-request read/write budget, isolated across concurrent ASGI requests."""

import time
from contextlib import contextmanager
from contextvars import ContextVar

import httpx

deadline = ContextVar("salesforce_deadline", default=None)


@contextmanager
def request_budget(enabled):
    token = deadline.set(time.monotonic() + 60 if enabled else None)
    try:
        yield
    finally:
        deadline.reset(token)


def timeout():
    end = deadline.get()
    remaining = end - time.monotonic() if end is not None else 20
    if remaining <= 0:
        raise TimeoutError("Salesforce request budget exhausted")
    # Leave room for connect/read/write/pool phases within the remaining budget.
    seconds = min(20, remaining / 4) if end is not None else 20
    return httpx.Timeout(seconds, connect=min(5, seconds))
