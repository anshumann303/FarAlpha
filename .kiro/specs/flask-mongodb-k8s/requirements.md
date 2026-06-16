# Requirements Document

## Introduction

This feature delivers a production-ready Python Flask web application backed by MongoDB, fully containerized with Docker, and deployed on Kubernetes (Minikube). The system exposes a REST API for reading and writing records, uses a StatefulSet with persistent storage for MongoDB, and includes Horizontal Pod Autoscaling for the Flask tier. The deliverable includes all Kubernetes manifests, a production-ready Dockerfile, application source code, and a comprehensive README covering architecture, deployment, testing, DNS resolution, and design decisions.

## Glossary

- **Flask_App**: The Python Flask web application running in a Kubernetes Deployment.
- **MongoDB**: The MongoDB database server running in a Kubernetes StatefulSet.
- **MongoDB_Service**: The ClusterIP Kubernetes Service exposing MongoDB inside the cluster.
- **Flask_Service**: The NodePort Kubernetes Service exposing the Flask_App externally.
- **HPA**: Horizontal Pod Autoscaler managing Flask_App replica count.
- **Secret**: A Kubernetes Secret resource storing MongoDB credentials.
- **PV**: A Kubernetes PersistentVolume providing durable storage backed by hostPath (Minikube).
- **PVC**: A Kubernetes PersistentVolumeClaim bound to the PV for use by MongoDB.
- **Namespace**: The Kubernetes Namespace isolating all project resources.
- **Dockerfile**: The Docker build specification for the Flask_App container image.
- **README**: The project documentation file covering architecture, setup, testing, and design decisions.
- **API**: The HTTP interface exposed by the Flask_App.
- **Record**: A JSON document stored in MongoDB via the POST /data endpoint.
- **Connection_String**: The MongoDB URI used by Flask_App to connect to MongoDB.

---

## Requirements

### Requirement 1: Flask Application Endpoints

**User Story:** As an API consumer, I want a Flask web application with well-defined endpoints, so that I can retrieve the current server time and manage records stored in MongoDB.

#### Acceptance Criteria

1. WHEN a GET request is received at `/`, THE Flask_App SHALL return an HTTP 200 response with a plain-text or JSON body containing the string `"Welcome to the Flask app! The current time is: "` followed by the current server date and time.
2. WHEN a GET request is received at `/data`, THE Flask_App SHALL return an HTTP 200 response containing all Records currently stored in MongoDB as a JSON array.
3. WHEN a POST request is received at `/data` with a valid JSON payload, THE Flask_App SHALL insert the payload as a Record into MongoDB and return an HTTP 201 response with body `{"status": "Data inserted"}`.
4. IF a POST request is received at `/data` with a missing or malformed JSON body, THEN THE Flask_App SHALL return an HTTP 400 response with a descriptive error message.
5. IF MongoDB is unreachable when any endpoint is called, THEN THE Flask_App SHALL return an HTTP 503 response and log the connection error.

---

### Requirement 2: MongoDB Authentication and Connectivity

**User Story:** As a system operator, I want MongoDB to require authentication and for credentials to be stored securely, so that the database is not accessible without valid credentials.

#### Acceptance Criteria

1. THE MongoDB SHALL run with authentication enabled, requiring a username and password for all client connections.
2. THE Secret SHALL store the MongoDB username (`admin`) and password (`password`) as base64-encoded values in a Kubernetes Secret resource named `mongo-secret`.
3. WHEN the Flask_App starts, THE Flask_App SHALL read the MongoDB username, password, and host from environment variables injected by the Secret and construct the Connection_String `mongodb://admin:password@mongodb-service:27017/`.
4. IF the Flask_App cannot authenticate to MongoDB at startup, THEN THE Flask_App SHALL log an authentication error with sufficient detail for diagnosis and exit with a non-zero status code.
5. THE MongoDB SHALL accept connections only on port 27017 within the cluster.

---

### Requirement 3: Python Application Code Quality

**User Story:** As a developer, I want the Flask application to follow production-ready Python practices, so that the codebase is maintainable, observable, and reliable.

#### Acceptance Criteria

1. THE Flask_App source code SHALL be contained in a file named `app.py` using Python 3.10 or later syntax.
2. THE Flask_App SHALL include a `requirements.txt` file listing pinned versions of `Flask`, `pymongo`, and `python-dotenv` as direct dependencies.
3. THE Flask_App SHALL use Python's standard `logging` module to emit structured log messages for all incoming requests, successful database operations, and error conditions.
4. WHEN an unhandled exception occurs during request processing, THE Flask_App SHALL catch the exception, log the full traceback, and return an HTTP 500 response with a safe error message that does not expose internal details.
5. THE Flask_App SHALL load environment variables using `python-dotenv` when a `.env` file is present, falling back to system environment variables when it is not.

---

### Requirement 4: Docker Image Build

**User Story:** As a DevOps engineer, I want a minimal, production-ready Docker image for the Flask application, so that deployments are fast, secure, and reproducible.

#### Acceptance Criteria

1. THE Dockerfile SHALL use `python:3.10-slim` as the base image.
2. THE Dockerfile SHALL copy `requirements.txt` into the image and install dependencies before copying application source code, so that dependency layers are cached independently of source changes.
3. THE Dockerfile SHALL expose port 5000 using the `EXPOSE` instruction.
4. THE Dockerfile SHALL include inline comments explaining each significant build step.
5. THE Dockerfile SHALL set a non-root user for running the application process to reduce the container attack surface.
6. WHEN the container starts, THE Dockerfile SHALL define a default `CMD` or `ENTRYPOINT` that launches the Flask_App on host `0.0.0.0` and port `5000`.

---

### Requirement 5: Kubernetes Namespace

**User Story:** As a cluster operator, I want all project resources isolated in a dedicated Namespace, so that they do not interfere with other workloads on the cluster.

#### Acceptance Criteria

1. THE Namespace SHALL be defined in `k8s/namespace.yaml` and applied before any other Kubernetes resource.
2. THE Namespace manifest SHALL include standard labels identifying the project.
3. ALL Kubernetes resources (Deployment, StatefulSet, Services, Secret, PV, PVC, HPA) SHALL reference the same Namespace.

---

### Requirement 6: Kubernetes Secret for Credentials

**User Story:** As a security-conscious operator, I want MongoDB credentials stored as a Kubernetes Secret rather than in plain-text manifests, so that sensitive data is not exposed in source control.

#### Acceptance Criteria

1. THE Secret SHALL be defined in `k8s/mongo-secret.yaml` with `type: Opaque`.
2. THE Secret SHALL contain two keys: `mongo-username` and `mongo-password` with base64-encoded values.
3. WHEN the Flask_App Pod is scheduled, THE Flask_App SHALL receive the Secret values as environment variables via `secretKeyRef` references in the Pod spec.
4. WHEN the MongoDB Pod is scheduled, THE MongoDB SHALL receive the Secret values as environment variables `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` via `secretKeyRef` references in the Pod spec.

---

### Requirement 7: Persistent Storage for MongoDB

**User Story:** As a data operator, I want MongoDB data to survive Pod restarts, so that records are not lost when the MongoDB Pod is rescheduled.

#### Acceptance Criteria

1. THE PV SHALL be defined in `k8s/pv.yaml` with a capacity of 1Gi, `accessModes: [ReadWriteOnce]`, and `hostPath` storage for Minikube compatibility.
2. THE PVC SHALL be defined in `k8s/pvc.yaml` requesting 1Gi with `accessModes: [ReadWriteOnce]` and bound to the PV.
3. THE MongoDB StatefulSet Pod template SHALL mount the PVC at `/data/db`.
4. IF the MongoDB Pod is deleted and rescheduled, THEN THE MongoDB SHALL reattach the same PVC and serve the previously stored Records without data loss.

---

### Requirement 8: MongoDB StatefulSet

**User Story:** As a cluster operator, I want MongoDB deployed as a StatefulSet, so that the database has a stable network identity and ordered, graceful scaling behavior.

#### Acceptance Criteria

1. THE MongoDB StatefulSet SHALL be defined in `k8s/mongodb-statefulset.yaml` using the `mongo:latest` image with 1 replica.
2. THE MongoDB StatefulSet SHALL set resource requests of `cpu: 200m` and `memory: 256Mi` and resource limits of `cpu: 500m` and `memory: 512Mi` on the MongoDB container.
3. THE MongoDB StatefulSet SHALL pass `MONGO_INITDB_ROOT_USERNAME` and `MONGO_INITDB_ROOT_PASSWORD` environment variables sourced from the Secret.
4. THE MongoDB StatefulSet Pod template SHALL include a readiness probe that checks MongoDB is accepting connections on port 27017 before the Pod is marked ready.

---

### Requirement 9: MongoDB Service

**User Story:** As a developer, I want a stable DNS name for MongoDB inside the cluster, so that the Flask application can connect to MongoDB using a predictable hostname.

#### Acceptance Criteria

1. THE MongoDB_Service SHALL be defined in `k8s/mongodb-service.yaml` with `type: ClusterIP` and `name: mongodb-service`.
2. THE MongoDB_Service SHALL expose port 27017 and forward traffic to the MongoDB StatefulSet Pod on port 27017.
3. WHEN the Flask_App resolves the hostname `mongodb-service`, THE MongoDB_Service SHALL return the cluster-internal IP address of the MongoDB Pod.

---

### Requirement 10: Flask Deployment

**User Story:** As a platform engineer, I want the Flask application deployed as a Kubernetes Deployment, so that the desired number of replicas is maintained and rolling updates are supported.

#### Acceptance Criteria

1. THE Flask_App Deployment SHALL be defined in `k8s/flask-deployment.yaml` with `name: flask-app` and `replicas: 2`.
2. THE Flask_App Deployment SHALL reference the image `yourdockerhub/flask-app:v1`.
3. THE Flask_App Deployment SHALL set resource requests of `cpu: 200m` and `memory: 256Mi` and resource limits of `cpu: 500m` and `memory: 512Mi` on the Flask container.
4. THE Flask_App Deployment SHALL include a `readinessProbe` performing an HTTP GET on `/` at port 5000, with an `initialDelaySeconds` of at least 5 seconds.
5. THE Flask_App Deployment SHALL include a `livenessProbe` performing an HTTP GET on `/` at port 5000, with an `initialDelaySeconds` of at least 15 seconds.
6. THE Flask_App Deployment Pod template SHALL receive MongoDB credentials from the Secret via environment variables.

---

### Requirement 11: Flask Service

**User Story:** As an end user, I want to access the Flask API from outside the Kubernetes cluster, so that I can interact with the application from my local machine.

#### Acceptance Criteria

1. THE Flask_Service SHALL be defined in `k8s/flask-service.yaml` with `type: NodePort` and `name: flask-service`.
2. THE Flask_Service SHALL forward external traffic on a NodePort to port 5000 on Flask_App Pods.
3. WHEN a request is sent to the Minikube node IP on the assigned NodePort, THE Flask_Service SHALL route the request to an available Flask_App Pod.

---

### Requirement 12: Horizontal Pod Autoscaling

**User Story:** As a platform engineer, I want the Flask application to scale automatically based on CPU load, so that the system handles traffic spikes without manual intervention.

#### Acceptance Criteria

1. THE HPA SHALL be defined in `k8s/hpa.yaml` using `apiVersion: autoscaling/v2`.
2. THE HPA SHALL target the `flask-app` Deployment with a minimum of 2 replicas and a maximum of 5 replicas.
3. WHEN average CPU utilization across Flask_App Pods exceeds 70%, THE HPA SHALL increase the replica count by at least 1, up to the maximum of 5.
4. WHEN average CPU utilization across Flask_App Pods drops below 70%, THE HPA SHALL decrease the replica count toward the minimum of 2.

---

### Requirement 13: Project File Structure

**User Story:** As a developer, I want the project to follow a well-defined folder structure, so that files are easy to locate and the project is straightforward to onboard.

#### Acceptance Criteria

1. THE project root SHALL contain `app.py`, `requirements.txt`, `Dockerfile`, and `README.md`.
2. THE project SHALL contain a `k8s/` subdirectory with exactly the following files: `namespace.yaml`, `mongo-secret.yaml`, `pv.yaml`, `pvc.yaml`, `mongodb-statefulset.yaml`, `mongodb-service.yaml`, `flask-deployment.yaml`, `flask-service.yaml`, `hpa.yaml`.
3. THE Flask_App SHALL not include any files containing plaintext credentials in the project root or `k8s/` directory that would be committed to source control.

---

### Requirement 14: README Documentation

**User Story:** As a new team member, I want comprehensive documentation in the README, so that I can understand the architecture, deploy the system, and test all components without prior knowledge of the project.

#### Acceptance Criteria

1. THE README SHALL include an architecture diagram (ASCII or Mermaid) illustrating the relationships between the Flask_App, MongoDB_Service, MongoDB, PV, HPA, and external traffic.
2. THE README SHALL include a folder structure listing all project files with a brief description of each.
3. THE README SHALL include a prerequisites section listing required tools (Docker, Minikube, kubectl) with minimum version recommendations.
4. THE README SHALL include step-by-step instructions for building the Docker image and pushing it to a registry.
5. THE README SHALL include step-by-step instructions for starting Minikube, enabling the metrics-server addon (required for HPA), and applying all Kubernetes manifests in the correct order.
6. THE README SHALL include instructions for verifying the deployment status of all Pods, Services, PVCs, and the HPA.
7. THE README SHALL include `curl` or equivalent command examples for testing all three API endpoints (GET `/`, GET `/data`, POST `/data`).
8. THE README SHALL include instructions for connecting to MongoDB from within the cluster to verify stored Records.
9. THE README SHALL include instructions for testing DNS resolution of `mongodb-service` from within a Flask_App Pod.
10. THE README SHALL include instructions for triggering and observing HPA scaling behavior.
11. THE README SHALL include instructions for viewing Flask_App and MongoDB logs using `kubectl logs`.
12. THE README SHALL include a troubleshooting section covering at least: Pod CrashLoopBackOff, PVC Pending state, and HPA showing `<unknown>` metrics.
13. THE README SHALL include cleanup instructions for removing all deployed resources and stopping Minikube.
14. THE README SHALL include a design decisions section explaining the rationale for: using a Deployment for Flask_App, using a StatefulSet for MongoDB, using a Secret for credentials, using ClusterIP for MongoDB_Service, using NodePort for Flask_Service, using a PersistentVolume, and using HPA. Each decision SHALL include alternatives considered and production considerations.
