"""
Unit tests for Flask endpoints.

Tests use Flask's built-in test client with app.client mocked so no real
MongoDB connection is needed.

Tasks: 3.1 (GET /), 3.2 (GET /data), 3.3 (POST /data)
"""
import json
from unittest.mock import MagicMock

import pytest
from bson import ObjectId
from pymongo.errors import ConnectionFailure

# app is imported after conftest.py has patched pymongo.MongoClient
import app as flask_app_module
from app import app


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    """Return a Flask test client with testing mode enabled."""
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


def _make_collection_mock(documents=None):
    """Return a mock for app.client['flask_db']['records']."""
    coll_mock = MagicMock()
    if documents is not None:
        coll_mock.find.return_value = documents
    return coll_mock


def _set_collection(mock_coll):
    """Wire the collection mock into the module-level client mock."""
    flask_app_module.client.__getitem__.return_value.__getitem__.return_value = mock_coll


# ---------------------------------------------------------------------------
# Task 3.1 — Unit tests for GET /
# ---------------------------------------------------------------------------

class TestGetIndex:
    """Tests for GET / endpoint.  Requirements: 1.1, 1.5"""

    def test_index_returns_200_with_welcome_string(self, client):
        """GET / returns 200 and a body containing the welcome prefix."""
        response = client.get("/")

        assert response.status_code == 200
        body = response.get_data(as_text=True)
        assert "Welcome to the Flask app! The current time is:" in body

    def test_index_returns_503_when_db_unreachable(self, client):
        """GET / returns 503 when MongoDB ping raises ConnectionFailure."""
        flask_app_module.client.admin.command.side_effect = ConnectionFailure("timeout")

        response = client.get("/")

        assert response.status_code == 503
        data = response.get_json()
        assert data == {"error": "Database unavailable"}

        # Restore for subsequent tests (reset_mock_client fixture also does this)
        flask_app_module.client.admin.command.side_effect = None


# ---------------------------------------------------------------------------
# Task 3.2 — Unit tests for GET /data
# ---------------------------------------------------------------------------

class TestGetData:
    """Tests for GET /data endpoint.  Requirements: 1.2, 1.5"""

    def test_get_data_empty_collection_returns_200_and_empty_list(self, client):
        """GET /data with no documents returns 200 and an empty JSON array."""
        coll_mock = _make_collection_mock(documents=[])
        _set_collection(coll_mock)

        response = client.get("/data")

        assert response.status_code == 200
        assert response.get_json() == []

    def test_get_data_returns_documents_with_objectid_serialised(self, client):
        """GET /data serialises ObjectId _id fields to strings."""
        oid = ObjectId("507f1f77bcf86cd799439011")
        coll_mock = _make_collection_mock(
            documents=[{"_id": oid, "name": "Alice", "age": 30}]
        )
        _set_collection(coll_mock)

        response = client.get("/data")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 1
        # _id must be a plain string, not an ObjectId
        assert data[0]["_id"] == "507f1f77bcf86cd799439011"
        assert isinstance(data[0]["_id"], str)
        assert data[0]["name"] == "Alice"
        assert data[0]["age"] == 30

    def test_get_data_multiple_documents(self, client):
        """GET /data returns all documents, each with _id as string."""
        docs = [
            {"_id": ObjectId("507f1f77bcf86cd799439011"), "key": "a"},
            {"_id": ObjectId("507f1f77bcf86cd799439012"), "key": "b"},
        ]
        coll_mock = _make_collection_mock(documents=docs)
        _set_collection(coll_mock)

        response = client.get("/data")

        assert response.status_code == 200
        data = response.get_json()
        assert len(data) == 2
        for item in data:
            assert isinstance(item["_id"], str)

    def test_get_data_returns_503_when_db_unreachable(self, client):
        """GET /data returns 503 when collection access raises ConnectionFailure."""
        coll_mock = MagicMock()
        coll_mock.find.side_effect = ConnectionFailure("unreachable")
        _set_collection(coll_mock)

        response = client.get("/data")

        assert response.status_code == 503
        assert response.get_json() == {"error": "Database unavailable"}


# ---------------------------------------------------------------------------
# Task 3.3 — Unit tests for POST /data
# ---------------------------------------------------------------------------

class TestPostData:
    """Tests for POST /data endpoint.  Requirements: 1.3, 1.4, 1.5"""

    def test_post_valid_json_returns_201_with_status(self, client):
        """POST /data with valid JSON object returns 201 and success body."""
        coll_mock = MagicMock()
        coll_mock.insert_one.return_value = MagicMock()
        _set_collection(coll_mock)

        response = client.post(
            "/data",
            data=json.dumps({"name": "Bob", "value": 42}),
            content_type="application/json",
        )

        assert response.status_code == 201
        assert response.get_json() == {"status": "Data inserted"}
        coll_mock.insert_one.assert_called_once()

    def test_post_empty_body_returns_400(self, client):
        """POST /data with no body returns 400."""
        response = client.post("/data", data="", content_type="application/json")

        assert response.status_code == 400

    def test_post_malformed_json_returns_400(self, client):
        """POST /data with malformed JSON string returns 400."""
        response = client.post(
            "/data", data="not-json", content_type="application/json"
        )

        assert response.status_code == 400

    def test_post_json_array_returns_400(self, client):
        """POST /data with a JSON array (not an object) returns 400."""
        response = client.post(
            "/data",
            data=json.dumps([1, 2, 3]),
            content_type="application/json",
        )

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data

    def test_post_json_string_returns_400(self, client):
        """POST /data with a JSON string (not an object) returns 400."""
        response = client.post(
            "/data",
            data=json.dumps("just a string"),
            content_type="application/json",
        )

        assert response.status_code == 400

    def test_post_no_content_type_returns_400(self, client):
        """POST /data with missing Content-Type returns 400."""
        response = client.post("/data", data='{"key": "val"}')

        assert response.status_code == 400

    def test_post_returns_503_when_db_unreachable(self, client):
        """POST /data returns 503 when insert raises ConnectionFailure."""
        coll_mock = MagicMock()
        coll_mock.insert_one.side_effect = ConnectionFailure("unreachable")
        _set_collection(coll_mock)

        response = client.post(
            "/data",
            data=json.dumps({"key": "val"}),
            content_type="application/json",
        )

        assert response.status_code == 503
        assert response.get_json() == {"error": "Database unavailable"}
