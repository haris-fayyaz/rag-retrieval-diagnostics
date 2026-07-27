import pytest

from app.core.rate_limit import rate_limiter


@pytest.fixture(autouse=True)
def _reset_rate_limiter():
    """
    Rate limiter state lives in one shared, module-level singleton (see
    app/core/rate_limit.py) - without this, whichever test runs first
    quietly uses up another test's quota, and unrelated tests start
    failing with 429 depending on run order. Clear it before every test.
    """
    rate_limiter._hits.clear()
    yield