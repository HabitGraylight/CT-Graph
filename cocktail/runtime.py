"""Request-local boundary: cloud requests may only use public default knowledge."""
from contextlib import contextmanager
from contextvars import ContextVar

PUBLIC_ONLY = ContextVar('cocktail_public_only', default=False)


@contextmanager
def public_runtime():
    token = PUBLIC_ONLY.set(True)
    try:
        yield
    finally:
        PUBLIC_ONLY.reset(token)
