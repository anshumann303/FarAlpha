"""
Flask application backed by MongoDB.

Exposes three endpoints:
  GET  /       — welcome message with current timestamp
  GET  /data   — return all records from MongoDB as a JSON array
  POST /data   — insert a JSON object into MongoDB
"""

import logging
import os
import sys
from datetime import datetime

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure

# ---------------------------------------------------------------------------
# Logging — configure at module level before anything else
# ---------------------------------------------------------------------------
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
)

# ---------------------------------------------------------------------------
# Environment variables — load from .env if present, fall back to system env
# ---------------------------------------------------------------------------
load_dotenv()

MONGO_USERNAME = os.environ.get("MONGO_USERNAME", "")
MONGO_PASSWORD = os.environ.get("MONGO_PASSWORD", "")
MONGO_HOST = os.environ.get("MONGO_HOST", "mongodb-service")

# ---------------------------------------------------------------------------
# Connection string helper (pure function — used directly in property tests)
# ---------------------------------------------------------------------------


def build_connection_string(username: str, password: str, host: str) -> str:
    """Return a MongoDB connection URI for the given credentials and host."""
    return f"mongodb://{username}:{password}@{host}:27017/"


# ---------------------------------------------------------------------------
# MongoDB client — initialised at startup; exit on auth failure
# ---------------------------------------------------------------------------
_connection_string = build_connection_string(MONGO_USERNAME, MONGO_PASSWORD, MONGO_HOST)
client = MongoClient(_connection_string)

try:
    client.admin.command("ping")
    logging.info("MongoDB connection established successfully.")
except (ConnectionFailure, OperationFailure) as exc:
    logging.critical("Failed to authenticate / connect to MongoDB at startup: %s", exc)
    sys.exit(1)

# ---------------------------------------------------------------------------
# Flask application
# ---------------------------------------------------------------------------
app = Flask(__name__)


# ---------------------------------------------------------------------------
# GET /
# ---------------------------------------------------------------------------
@app.route("/", methods=["GET"])
def index():
    """Return a welcome message and the current server time."""
    logging.info("GET / called")
    try:
        client.admin.command("ping")
    except (ConnectionFailure, OperationFailure) as exc:
        logging.error("Database unavailable on GET /: %s", exc)
        return jsonify({"error": "Database unavailable"}), 503

    return f"Welcome to the Flask app! The current time is: {datetime.now()}", 200


# ---------------------------------------------------------------------------
# GET /data
# ---------------------------------------------------------------------------
@app.route("/data", methods=["GET"])
def get_data():
    """Return all records from the flask_db.records collection as JSON."""
    logging.info("GET /data called")
    try:
        collection = client["flask_db"]["records"]
        documents = list(collection.find({}))
        # ObjectId is not JSON-serialisable — convert to string
        for doc in documents:
            doc["_id"] = str(doc["_id"])
        return jsonify(documents), 200
    except (ConnectionFailure, OperationFailure) as exc:
        logging.error("Database unavailable on GET /data: %s", exc)
        return jsonify({"error": "Database unavailable"}), 503


# ---------------------------------------------------------------------------
# POST /data
# ---------------------------------------------------------------------------
@app.route("/data", methods=["POST"])
def post_data():
    """Insert a JSON object into flask_db.records and return 201."""
    logging.info("POST /data called")

    body = request.get_json(silent=True)

    # Reject missing body, non-object JSON (e.g. arrays, scalars), or malformed JSON
    if body is None or not isinstance(body, dict):
        logging.warning("POST /data rejected: invalid JSON body (got %r)", body)
        return jsonify({"error": "Invalid JSON body"}), 400

    try:
        collection = client["flask_db"]["records"]
        collection.insert_one(body)
        logging.info("Inserted record into flask_db.records")
        return jsonify({"status": "Data inserted"}), 201
    except (ConnectionFailure, OperationFailure) as exc:
        logging.error("Database unavailable on POST /data: %s", exc)
        return jsonify({"error": "Database unavailable"}), 503


# ---------------------------------------------------------------------------
# Global exception handler — catches anything not caught by route handlers
# ---------------------------------------------------------------------------
@app.errorhandler(Exception)
def handle_exception(exc):
    """Log the full traceback and return a safe 500 response."""
    logging.exception("Unhandled exception: %s", exc)
    return jsonify({"error": "Internal server error"}), 500


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
