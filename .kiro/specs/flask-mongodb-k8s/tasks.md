# Implementation Plan: flask-mongodb-k8s

## Overview

Implement a production-ready Python Flask application backed by MongoDB, containerized with Docker, and deployed on Kubernetes (Minikube). The implementation follows the dependency order: application code → Docker image → Kubernetes manifests → tests → documentation.

## Tasks

- [x] 1. Set up project structure and Python application dependencies
  - Create `requirements.txt` with pinned versions: `Flask==3.0.3`, `pymongo==4.7.2`, `python-dotenv==1.0.1`
  - Create the `k8s/` subdirectory (empty, to be populated in later tasks)
  - Create a `tests/unit/`, `tests/property/`, and `tests/smoke/` directory structure with `__init__.py` files
  - _Requirements: 3.2, 13.1, 13.2_

- [x] 2. Implement Flask application (`app.py`)
  - [x] 2.1 Implement module-level setup and MongoDB client initialization
    - Configure Python `logging` module at module level (format: timestamp, level, message)
    - Load environment variables via `python-dotenv` (`load_dotenv()`), falling back to system env vars
    - Read `MONGO_USERNAME`, `MONGO_PASSWORD`, `MONGO_HOST` from environment
    - Implement `build_connection_string(username, password, host)` as a pure function returning `mongodb://{username}:{password}@{host}:27017/`
    - Construct `MongoClient` using the connection string and run `client.admin.command('ping')` at startup; log CRITICAL and `sys.exit(1)` on auth failure
    - Create Flask app instance
    - _Requirements: 2.3, 2.4, 3.1, 3.3, 3.5_

  - [x] 2.2 Implement `GET /` endpoint
    - Return HTTP 200 with text body `"Welcome to the Flask app! The current time is: {datetime.now()}"` 
    - Wrap DB ping in try/except `ConnectionFailure`/`OperationFailure`; return 503 with `{"error": "Database unavailable"}` if unreachable
    - Log each incoming request at INFO level
    - _Requirements: 1.1, 1.5_

  - [x] 2.3 Implement `GET /data` endpoint
    - Query `flask_db.records` collection, serialize each document (convert `_id` ObjectId to string), return JSON array with HTTP 200
    - Wrap DB call in try/except; return 503 on connection/auth failure
    - _Requirements: 1.2, 1.5_

  - [x] 2.4 Implement `POST /data` endpoint
    - Parse request JSON (`request.get_json(silent=True)`); return HTTP 400 with `{"error": "Invalid JSON body"}` if body is missing, not a JSON object, or malformed
    - Insert valid JSON object into `flask_db.records`; return HTTP 201 with `{"status": "Data inserted"}`
    - Wrap DB call in try/except; return 503 on connection/auth failure
    - _Requirements: 1.3, 1.4, 1.5_

  - [x] 2.5 Implement global exception handler and `__main__` entry point
    - Add `@app.errorhandler(Exception)` that calls `logging.exception()` for full traceback, then returns `{"error": "Internal server error"}` with HTTP 500 (no internal details in body)
    - Add `if __name__ == '__main__': app.run(host='0.0.0.0', port=5000)`
    - _Requirements: 3.3, 3.4_

- [x] 3. Write unit tests for Flask endpoints (`tests/unit/test_endpoints.py`)
  - [ ]* 3.1 Write unit tests for `GET /` endpoint
    - Mock MongoDB client; assert 200 status and welcome string in response body
    - Mock connection failure; assert 503 returned
    - _Requirements: 1.1, 1.5_

  - [ ]* 3.2 Write unit tests for `GET /data` endpoint
    - Mock collection with empty result; assert 200 and `[]` returned
    - Mock collection with documents; assert ObjectId fields are serialized to strings
    - Mock connection failure; assert 503 returned
    - _Requirements: 1.2, 1.5_

  - [ ]* 3.3 Write unit tests for `POST /data` endpoint
    - POST valid JSON object; assert 201 and `{"status": "Data inserted"}`
    - POST empty body; assert 400
    - POST non-object JSON (array, string); assert 400
    - Mock connection failure; assert 503 returned
    - _Requirements: 1.3, 1.4, 1.5_

  - [ ]* 3.4 Write unit tests for error handling and startup behavior (`tests/unit/test_error_handling.py`)
    - Assert unhandled exception returns 500 with generic message and no traceback in body
    - Mock `client.admin.command('ping')` to raise; assert `sys.exit(1)` called and CRITICAL log emitted
    - Assert `.env` file values loaded when file present; assert system env vars used as fallback
    - _Requirements: 2.4, 3.4, 3.5_

- [x] 4. Write property-based tests for Flask application logic
  - [ ]* 4.1 Write property test for POST/GET round-trip (`tests/property/test_data_roundtrip.py`)
    - **Property 1: POST/GET data round-trip**
    - Use `@given(st.dictionaries(st.text(min_size=1), st.text() | st.integers()))` with `@settings(max_examples=100)`
    - POST arbitrary valid JSON object via Flask test client with mocked MongoDB; GET `/data`; assert posted key-value pairs present in response
    - **Validates: Requirements 1.2, 1.3**

  - [ ]* 4.2 Write property test for invalid JSON rejection (`tests/property/test_data_roundtrip.py`)
    - **Property 2: Invalid JSON body rejected**
    - Use `@given(st.one_of(st.just(""), st.binary(), st.text().filter(...)))` with `@settings(max_examples=100)`
    - POST invalid body; assert 400 returned and DB record count unchanged
    - **Validates: Requirements 1.4**

  - [ ]* 4.3 Write property test for connection string construction (`tests/property/test_connection_string.py`)
    - **Property 3: Connection string construction**
    - Use `@given(st.text(min_size=1), st.text(min_size=1), st.text(min_size=1))` with `@settings(max_examples=100)`
    - Call `build_connection_string(username, password, host)`; assert result equals `f"mongodb://{username}:{password}@{host}:27017/"`
    - **Validates: Requirements 2.3**

  - [ ]* 4.4 Write property test for safe 500 responses (`tests/property/test_exception_handling.py`)
    - **Property 4: Unhandled exceptions produce safe 500 responses**
    - Use `@given(st.text(min_size=1))` with `@settings(max_examples=100)`
    - Inject exception with arbitrary message; assert response status is 500, response body does not contain exception message, and log does contain full traceback
    - **Validates: Requirements 3.4**

- [x] 5. Checkpoint — Ensure all application tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. Create Dockerfile
  - Write `Dockerfile` using `python:3.10-slim` as base image
  - Create non-root user `appuser` (uid 1000) and group
  - Set working directory to `/app`
  - Copy `requirements.txt` first and run `pip install --no-cache-dir -r requirements.txt` (separate layer for cache efficiency)
  - Copy `app.py`
  - `EXPOSE 5000`
  - Switch to `appuser` with `USER appuser`
  - Set `CMD ["python", "app.py"]`
  - Add inline comments explaining each significant build step
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_

- [x] 7. Create Kubernetes Namespace manifest (`k8s/namespace.yaml`)
  - Define Namespace with `name: flask-mongodb-ns`
  - Add labels `project: flask-mongodb-k8s` and `env: demo`
  - _Requirements: 5.1, 5.2_

- [x] 8. Create Kubernetes Secret manifest (`k8s/mongo-secret.yaml`)
  - Define Secret with `name: mongo-secret`, `namespace: flask-mongodb-ns`, `type: Opaque`
  - Set `mongo-username: YWRtaW4=` (base64 of `admin`) and `mongo-password: cGFzc3dvcmQ=` (base64 of `password`)
  - _Requirements: 6.1, 6.2_

- [x] 9. Create PersistentVolume and PersistentVolumeClaim manifests
  - [x] 9.1 Create `k8s/pv.yaml`
    - Name: `mongodb-pv`, capacity `1Gi`, `accessModes: [ReadWriteOnce]`
    - `storageClassName: manual`, `persistentVolumeReclaimPolicy: Retain`
    - `hostPath.path: /mnt/data/mongodb`
    - _Requirements: 7.1_

  - [x] 9.2 Create `k8s/pvc.yaml`
    - Name: `mongodb-pvc`, namespace: `flask-mongodb-ns`
    - Request `1Gi`, `accessModes: [ReadWriteOnce]`, `storageClassName: manual`
    - _Requirements: 7.2_

- [x] 10. Create MongoDB StatefulSet manifest (`k8s/mongodb-statefulset.yaml`)
  - Name: `mongodb`, namespace: `flask-mongodb-ns`, `replicas: 1`
  - Image: `mongo:latest`, containerPort: 27017
  - `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` sourced from `mongo-secret` via `secretKeyRef`
  - Mount `mongodb-pvc` at `/data/db`
  - Resources: requests `cpu:200m, memory:256Mi`; limits `cpu:500m, memory:512Mi`
  - Readiness probe: TCP socket on port 27017, `initialDelaySeconds:10`, `periodSeconds:5`
  - _Requirements: 6.4, 7.3, 8.1, 8.2, 8.3, 8.4_

- [x] 11. Create MongoDB Service manifest (`k8s/mongodb-service.yaml`)
  - Name: `mongodb-service`, namespace: `flask-mongodb-ns`, type: `ClusterIP`
  - Port 27017 → targetPort 27017, selector `app: mongodb`
  - _Requirements: 9.1, 9.2_

- [x] 12. Create Flask Deployment manifest (`k8s/flask-deployment.yaml`)
  - Name: `flask-app`, namespace: `flask-mongodb-ns`, `replicas: 2`
  - Image: `yourdockerhub/flask-app:v1`, containerPort: 5000
  - `MONGO_USERNAME` and `MONGO_PASSWORD` sourced from `mongo-secret` via `secretKeyRef`; `MONGO_HOST: mongodb-service` as literal env var
  - Resources: requests `cpu:200m, memory:256Mi`; limits `cpu:500m, memory:512Mi`
  - Readiness probe: HTTP GET `/`, port 5000, `initialDelaySeconds:5`, `periodSeconds:10`
  - Liveness probe: HTTP GET `/`, port 5000, `initialDelaySeconds:15`, `periodSeconds:20`
  - _Requirements: 6.3, 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

- [x] 13. Create Flask Service manifest (`k8s/flask-service.yaml`)
  - Name: `flask-service`, namespace: `flask-mongodb-ns`, type: `NodePort`
  - Port 80 → targetPort 5000, selector `app: flask-app`
  - _Requirements: 11.1, 11.2_

- [x] 14. Create HPA manifest (`k8s/hpa.yaml`)
  - `apiVersion: autoscaling/v2`, name: `flask-hpa`, namespace: `flask-mongodb-ns`
  - Scale target: `flask-app` Deployment, `minReplicas: 2`, `maxReplicas: 5`
  - CPU metric: `AverageUtilization: 70`
  - _Requirements: 12.1, 12.2, 12.3, 12.4_

- [x] 15. Write smoke tests for Kubernetes manifest validation (`tests/smoke/test_manifests.py`)
  - [x]* 15.1 Write manifest smoke tests
    - Use `pyyaml` to load each manifest and assert required fields
    - `namespace.yaml`: name is `flask-mongodb-ns`, labels present
    - `mongo-secret.yaml`: type is `Opaque`, keys `mongo-username` and `mongo-password` present with correct base64 values
    - `pv.yaml`: capacity `1Gi`, accessModes `ReadWriteOnce`, storageClassName `manual`, hostPath set
    - `pvc.yaml`: requests `1Gi`, storageClassName `manual`, accessModes `ReadWriteOnce`
    - `mongodb-statefulset.yaml`: image `mongo:latest`, resource limits present, readiness probe defined, `secretKeyRef` env vars present
    - `flask-deployment.yaml`: replicas 2, resource limits present, readiness + liveness probes defined, `secretKeyRef` env vars present
    - `flask-service.yaml`: type `NodePort`, targetPort 5000
    - `mongodb-service.yaml`: type `ClusterIP`, port 27017
    - `hpa.yaml`: apiVersion `autoscaling/v2`, minReplicas 2, maxReplicas 5, CPU utilization target 70
    - _Requirements: 5.1–5.3, 6.1–6.4, 7.1–7.3, 8.1–8.4, 9.1–9.2, 10.1–10.6, 11.1–11.2, 12.1–12.4, 13.2_

- [x] 16. Checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [x] 17. Create README.md
  - [x] 17.1 Write architecture section with Mermaid diagram and request flow description
    - Include component diagram showing Flask, MongoDB, Services, HPA, PV/PVC, Secret relationships
    - Describe the full request flow from external client through NodePort → flask-service → flask-app → mongodb-service → mongodb-0 → PVC/PV
    - _Requirements: 14.1_

  - [x] 17.2 Write project structure, prerequisites, and build sections
    - List all project files with brief descriptions (folder structure tree)
    - List required tools (Docker, Minikube, kubectl) with minimum version recommendations
    - Provide step-by-step instructions for building the Docker image and pushing to a registry
    - _Requirements: 14.2, 14.3, 14.4_

  - [x] 17.3 Write deployment and verification sections
    - Step-by-step: start Minikube, enable metrics-server addon, apply all 9 manifests in dependency order
    - Commands to verify Pod, Service, PVC, and HPA status (`kubectl get` commands)
    - `curl` examples for all three API endpoints (GET `/`, GET `/data`, POST `/data`)
    - Instructions for connecting to MongoDB from within the cluster and verifying stored records
    - Instructions for testing DNS resolution of `mongodb-service` from inside a Flask Pod
    - Instructions for triggering HPA scaling and observing replica count changes
    - Instructions for viewing Flask and MongoDB logs with `kubectl logs`
    - _Requirements: 14.5, 14.6, 14.7, 14.8, 14.9, 14.10, 14.11_

  - [x] 17.4 Write troubleshooting, cleanup, and design decisions sections
    - Troubleshooting: Pod CrashLoopBackOff, PVC Pending, HPA showing `<unknown>` metrics
    - Cleanup: commands to delete all resources and stop Minikube
    - Design decisions: Deployment vs DaemonSet for Flask, StatefulSet vs Deployment for MongoDB, Secret vs ConfigMap for credentials, ClusterIP vs NodePort for MongoDB, NodePort vs LoadBalancer for Flask, PV/PVC vs emptyDir, HPA vs manual scaling — each with alternatives considered and production notes
    - _Requirements: 14.12, 14.13, 14.14_

- [x] 18. Final checkpoint — Ensure all tests pass
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP delivery
- The design document specifies Python as the implementation language (Hypothesis for PBT, pytest for unit/smoke tests)
- `build_connection_string` must be a standalone pure function in `app.py` to enable direct testing in Property 3
- Kubernetes manifests must be applied in the order specified in the design (namespace → secret → pv → pvc → statefulset → services → deployment → hpa)
- The `mongo-secret.yaml` contains base64-encoded credentials — do not store plaintext credentials in any committed file
- Property tests use Flask's test client with `unittest.mock` or `mongomock` to avoid requiring a live MongoDB instance
