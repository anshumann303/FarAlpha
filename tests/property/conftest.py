"""
conftest.py for property-based tests.

Patches pymongo.MongoClient before app.py is imported so the module-level
MongoClient construction and startup ping do not require a real MongoDB instance.
This mirrors tests/unit/conftest.py but is applied for the property test suite.
"""
from unittest.mock import MagicMock, patch

# Start the patch at module load time (before any test file imports app).
_mongo_patcher = patch("pymongo.MongoClient")
_mock_mongo_class = _mongo_patcher.start()

# Make the mock client behave sensibly: ping succeeds, subscript access works.
_mock_client_instance = MagicMock()
_mock_mongo_class.return_value = _mock_client_instance
_mock_client_instance.admin.command.return_value = {"ok": 1}
