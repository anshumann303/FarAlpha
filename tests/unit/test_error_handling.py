"""
Unit tests for error handling and startup behaviour.

Task 3.4 — Requirements: 2.4, 3.4, 3.5
"""
import importlib
import logging
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from pymongo.errors import ConnectionFailure, OperationFailure

import app as flask_app_module
from app import app

# ---------------------------------------------------------------------------
# Register test-only routes at module level — BEFORE any test client makes a
# request, so Flask 3.x's "setup finished" guard is not triggered.
# ---------------------------------------------------------------------------

@app.route("/boom", methods=["GET"])
def boom():
    raise RuntimeError("top-secret internal message")


@app.route("/boom2", methods=["GET"])
def boom2():
    raise ValueError("sensitive detail: secret_token=abc123")


@app.route("/boom3", methods=["GET"])
def boom3():
    raise RuntimeError("unique-error-message-xyz")


# ---------------------------------------------------------------------------
# Fixture: Flask test client
# ---------------------------------------------------------------------------

@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as c:
        yield c


# ---------------------------------------------------------------------------
# Task 3.4a — Unhandled exception returns 500 with generic message (Req 3.4)
# ---------------------------------------------------------------------------

class TestUnhandledExceptionHandler:
    """The global error handler must return 500 without leaking internals."""

    def test_unhandled_exception_returns_500(self, client):
        """An endpoint that raises an unexpected exception returns HTTP 500."""
        response = client.get("/boom")

        assert response.status_code == 500
        data = response.get_json()
        assert data == {"error": "Internal server error"}

    def test_unhandled_exception_body_contains_no_traceback(self, client):
        """The 500 response body must not include any stack-trace text."""
        response = client.get("/boom2")

        assert response.status_code == 500
        body = response.get_data(as_text=True)
        # Must not leak internal message or traceback keywords
        assert "secret_token" not in body
        assert "Traceback" not in body
        assert "ValueError" not in body

    def test_unhandled_exception_is_logged(self, client, caplog):
        """The full traceback of an unhandled exception is recorded in logs."""
        with caplog.at_level(logging.ERROR):
            client.get("/boom3")

        # The log should contain the exception message (logged via logging.exception)
        assert "unique-error-message-xyz" in caplog.text


# ---------------------------------------------------------------------------
# Task 3.4b — Startup ping failure logs CRITICAL and calls sys.exit(1) (Req 2.4)
# ---------------------------------------------------------------------------

class TestStartupPingFailure:
    """When MongoDB ping fails at startup, app must log CRITICAL and exit."""

    def test_startup_ping_failure_calls_sys_exit(self):
        """If client.admin.command('ping') raises at import, sys.exit(1) is called."""
        with (
            patch("pymongo.MongoClient") as mock_client_class,
            patch("sys.exit") as mock_exit,
        ):
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            mock_instance.admin.command.side_effect = OperationFailure("auth failed")

            importlib.reload(flask_app_module)

            mock_exit.assert_called_once_with(1)

    def test_startup_ping_failure_logs_critical(self, caplog):
        """If client.admin.command('ping') raises at import, CRITICAL is logged."""
        with (
            patch("pymongo.MongoClient") as mock_client_class,
            patch("sys.exit"),  # prevent actual exit
        ):
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            mock_instance.admin.command.side_effect = ConnectionFailure("no mongo")

            with caplog.at_level(logging.CRITICAL):
                importlib.reload(flask_app_module)

            assert any(
                record.levelno == logging.CRITICAL for record in caplog.records
            ), "Expected a CRITICAL log record on startup ping failure"


# ---------------------------------------------------------------------------
# Task 3.4c — .env file loading and system env fallback (Req 3.5)
# ---------------------------------------------------------------------------

class TestEnvLoading:
    """Verify python-dotenv behaviour: .env takes precedence, system env is fallback."""

    def test_dotenv_values_loaded_when_env_file_present(self, tmp_path, monkeypatch):
        """When a .env file exists, its values are loaded into the environment."""
        env_file = tmp_path / ".env"
        env_file.write_text(
            "MONGO_USERNAME=dotenv_user\n"
            "MONGO_PASSWORD=dotenv_pass\n"
            "MONGO_HOST=dotenv_host\n"
        )

        # Reload with patched load_dotenv that reads our temp file
        with (
            patch("pymongo.MongoClient") as mock_client_class,
            patch("sys.exit"),
            patch(
                "dotenv.load_dotenv",
                side_effect=lambda: _load_env_from_file(str(env_file)),
            ),
        ):
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            mock_instance.admin.command.return_value = {"ok": 1}

            importlib.reload(flask_app_module)

            # The connection string built at module level uses the env vars
            call_args = mock_client_class.call_args
            connection_string = call_args[0][0]
            assert "dotenv_user" in connection_string
            assert "dotenv_pass" in connection_string
            assert "dotenv_host" in connection_string

    def test_system_env_vars_used_as_fallback_when_no_env_file(self, monkeypatch):
        """When no .env file is present, system env vars are used."""
        monkeypatch.setenv("MONGO_USERNAME", "sys_user")
        monkeypatch.setenv("MONGO_PASSWORD", "sys_pass")
        monkeypatch.setenv("MONGO_HOST", "sys_host")

        with (
            patch("pymongo.MongoClient") as mock_client_class,
            patch("sys.exit"),
            patch("dotenv.load_dotenv"),  # no-op: simulates absent .env
        ):
            mock_instance = MagicMock()
            mock_client_class.return_value = mock_instance
            mock_instance.admin.command.return_value = {"ok": 1}

            importlib.reload(flask_app_module)

            call_args = mock_client_class.call_args
            connection_string = call_args[0][0]
            assert "sys_user" in connection_string
            assert "sys_pass" in connection_string
            assert "sys_host" in connection_string


# ---------------------------------------------------------------------------
# Private helper
# ---------------------------------------------------------------------------

def _load_env_from_file(path: str):
    """Load key=value pairs from a file into os.environ (mimics dotenv behaviour)."""
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ[key.strip()] = value.strip()
