"""
Property-based test for safe 500 responses on unhandled exceptions.

Feature: flask-mongodb-k8s
Property 4: Unhandled exceptions produce safe 500 responses
            — Validates: Requirements 3.4
"""
import logging
import logging.handlers

from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# conftest.py has already patched pymongo.MongoClient at collection time.
from app import app

# ---------------------------------------------------------------------------
# Register the test route once at module load time.  We swap the view
# function on each test invocation (safe because Hypothesis runs examples
# sequentially in the same process).
# ---------------------------------------------------------------------------
_TEST_ROUTE = "/test_exc_property_pbt"


def _placeholder():  # pragma: no cover
    raise RuntimeError("placeholder")


app.add_url_rule(
    _TEST_ROUTE,
    endpoint="test_exc_property_pbt",
    view_func=_placeholder,
)


# ---------------------------------------------------------------------------
# Property 4: Unhandled exceptions produce safe 500 responses
# Validates: Requirements 3.4
# ---------------------------------------------------------------------------

_SAFE_ERROR_BODY = {"error": "Internal server error"}

# Generate strings that are long enough and distinctive enough that they
# cannot accidentally be a substring of the fixed 35-char safe-error JSON.
# Using min_size=36 guarantees the generated message is longer than the entire
# response body, so the substring check is always meaningful.
_distinct_message = st.text(min_size=36).filter(lambda s: s.strip())


@given(_distinct_message)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_unhandled_exception_returns_safe_500(exception_message: str):
    """
    **Property 4: Unhandled exceptions produce safe 500 responses**

    For any exception message string, when an unhandled exception with that
    message is raised during request processing:
      - The response status SHALL be 500.
      - The response body SHALL be exactly the safe generic error JSON (no internal
        details, no traceback).
      - The application log SHALL contain the full traceback (the message IS present).

    **Validates: Requirements 3.4**
    """
    # Swap view function so this example's message is raised.
    def _raise_exc():
        raise RuntimeError(exception_message)

    app.view_functions["test_exc_property_pbt"] = _raise_exc

    # Capture log records using a plain in-memory handler — no pytest fixture needed.
    log_records = []

    class _ListHandler(logging.Handler):
        def emit(self, record):
            log_records.append(self.format(record))

    handler = _ListHandler()
    handler.setLevel(logging.ERROR)
    # Use a formatter that includes exception info (traceback)
    handler.setFormatter(logging.Formatter("%(message)s\n%(exc_info)s"))

    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    try:
        app.config["TESTING"] = True
        with app.test_client() as client:
            response = client.get(_TEST_ROUTE)

        # 1. Status must be 500
        assert response.status_code == 500, (
            f"Expected 500, got {response.status_code}"
        )

        # 2. Response body must be exactly the safe generic error — no internal details.
        #    This is the primary correctness check: proves no exception content leaked.
        body_json = response.get_json()
        assert body_json == _SAFE_ERROR_BODY, (
            f"Response body must be the safe generic error.\n"
            f"Got: {response.get_data(as_text=True)!r}"
        )
        # With min_size=36, the generated message is longer than the entire response
        # body, so this substring check is always meaningful (never a false positive).
        body_text = response.get_data(as_text=True)
        assert exception_message not in body_text, (
            f"Response body must not contain exception message {exception_message!r}.\n"
            f"Body: {body_text!r}"
        )

        # 3. The log MUST contain the exception message (full traceback recorded)
        combined_log = "\n".join(log_records)
        assert exception_message in combined_log, (
            f"Log should contain exception message {exception_message!r}.\n"
            f"Captured log: {combined_log!r}"
        )
    finally:
        root_logger.removeHandler(handler)
