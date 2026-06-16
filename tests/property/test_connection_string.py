"""
Property-based test for MongoDB connection string construction.

Feature: flask-mongodb-k8s
Property 3: Connection string construction — Validates: Requirements 2.3
"""
from hypothesis import given, settings
from hypothesis import strategies as st

# conftest.py has already patched pymongo.MongoClient at collection time.
from app import build_connection_string


# ---------------------------------------------------------------------------
# Property 3: Connection string construction
# Validates: Requirements 2.3
# ---------------------------------------------------------------------------

@given(
    st.text(min_size=1),
    st.text(min_size=1),
    st.text(min_size=1),
)
@settings(max_examples=100)
def test_connection_string_format(username: str, password: str, host: str):
    """
    **Property 3: Connection string construction**

    For any non-empty username, password, and host, build_connection_string()
    SHALL return exactly ``mongodb://{username}:{password}@{host}:27017/``
    with no characters omitted or reordered.

    **Validates: Requirements 2.3**
    """
    expected = f"mongodb://{username}:{password}@{host}:27017/"
    result = build_connection_string(username, password, host)
    assert result == expected, (
        f"Connection string mismatch.\n"
        f"  username={username!r}, password={password!r}, host={host!r}\n"
        f"  expected: {expected!r}\n"
        f"  got:      {result!r}"
    )
