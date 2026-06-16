"""
Property-based tests for POST/GET data round-trip and invalid JSON rejection.

Feature: flask-mongodb-k8s
Property 1: POST/GET data round-trip   — Validates: Requirements 1.2, 1.3
Property 2: Invalid JSON body rejected  — Validates: Requirements 1.4
"""
import json
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# conftest.py has already patched pymongo.MongoClient at collection time.
import app as flask_app_module
from app import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_valid_json_object(s: str) -> bool:
    """Return True only if s parses to a JSON *object* (dict)."""
    try:
        return isinstance(json.loads(s), dict)
    except (json.JSONDecodeError, ValueError):
        return False


# ---------------------------------------------------------------------------
# Property 1: POST/GET data round-trip
# Validates: Requirements 1.2, 1.3
# ---------------------------------------------------------------------------

@given(st.dictionaries(st.text(min_size=1), st.text() | st.integers()))
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_post_get_roundtrip(record):
    """
    **Property 1: POST/GET data round-trip**

    For any valid JSON object, POSTing it to /data then GETting /data SHALL
    return a JSON array containing a record with the same key-value pairs.

    **Validates: Requirements 1.2, 1.3**
    """
    # Build an in-memory store for this single test invocation.
    # insert_one adds an ObjectId-like string _id just as real MongoDB would.
    from bson import ObjectId

    in_memory_store = []

    def _insert_one(doc):
        stored = dict(doc)
        stored.setdefault("_id", ObjectId())
        in_memory_store.append(stored)

    coll_mock = MagicMock()
    coll_mock.insert_one.side_effect = _insert_one
    # find() returns a snapshot of the store (each entry already has _id)
    coll_mock.find.side_effect = lambda *a, **kw: list(in_memory_store)

    flask_app_module.client.__getitem__.return_value.__getitem__.return_value = coll_mock

    app.config["TESTING"] = True
    with app.test_client() as client:
        # POST the record
        post_resp = client.post(
            "/data",
            data=json.dumps(record),
            content_type="application/json",
        )
        assert post_resp.status_code == 201, (
            f"Expected 201, got {post_resp.status_code}: {post_resp.get_data(as_text=True)}"
        )

        # GET all records
        get_resp = client.get("/data")
        assert get_resp.status_code == 200

        returned = get_resp.get_json()
        assert isinstance(returned, list), f"Expected list, got {type(returned)}"
        assert len(returned) >= 1, "Expected at least one record in the response"

        # The last inserted record must contain all original key-value pairs
        last = returned[-1]
        for key, value in record.items():
            assert key in last, f"Key {key!r} missing from returned record"
            assert last[key] == value, (
                f"Value mismatch for key {key!r}: expected {value!r}, got {last[key]!r}"
            )


# ---------------------------------------------------------------------------
# Property 2: Invalid JSON body rejected
# Validates: Requirements 1.4
# ---------------------------------------------------------------------------

@given(
    st.one_of(
        st.just(""),
        st.binary(),
        st.text().filter(lambda s: not _is_valid_json_object(s)),
    )
)
@settings(max_examples=100, suppress_health_check=[HealthCheck.function_scoped_fixture])
def test_invalid_json_rejected(body):
    """
    **Property 2: Invalid JSON body rejected**

    Any POST to /data with a non-object body (empty, binary, non-JSON-object
    string) SHALL return HTTP 400 and the database record count SHALL remain
    unchanged.

    **Validates: Requirements 1.4**
    """
    insert_count = [0]

    coll_mock = MagicMock()
    coll_mock.insert_one.side_effect = lambda doc: insert_count.__setitem__(
        0, insert_count[0] + 1
    )

    flask_app_module.client.__getitem__.return_value.__getitem__.return_value = coll_mock

    app.config["TESTING"] = True
    with app.test_client() as client:
        if isinstance(body, bytes):
            resp = client.post(
                "/data",
                data=body,
                content_type="application/octet-stream",
            )
        else:
            resp = client.post(
                "/data",
                data=body,
                content_type="application/json",
            )

        assert resp.status_code == 400, (
            f"Expected 400 for invalid body {body!r}, got {resp.status_code}"
        )
        assert insert_count[0] == 0, (
            f"DB should not have been written; got {insert_count[0]} insert(s)"
        )
