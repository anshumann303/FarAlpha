"""
conftest.py for unit tests.

Patches pymongo.MongoClient before app.py is imported so the module-level
MongoClient construction and startup ping do not require a real MongoDB instance.
"""
from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Session-scoped mock of MongoClient so that `import app` succeeds without a
# real MongoDB server.  This patch must be in place before the first import of
# app, which happens during pytest collection.
# ---------------------------------------------------------------------------

# Start the patch at module load time (before any test file imports app).
_mongo_patcher = patch("pymongo.MongoClient")
_mock_mongo_class = _mongo_patcher.start()

# Make the mock client behave sensibly: ping succeeds, subscript access works.
_mock_client_instance = MagicMock()
_mock_mongo_class.return_value = _mock_client_instance
_mock_client_instance.admin.command.return_value = {"ok": 1}


@pytest.fixture(autouse=True)
def reset_mock_client():
    """Reset mock state before every test so tests don't bleed into each other."""
    _mock_client_instance.reset_mock()
    # Restore default: ping succeeds
    _mock_client_instance.admin.command.return_value = {"ok": 1}
    yield
