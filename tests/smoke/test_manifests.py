"""
Smoke tests for Kubernetes manifest validation.

These tests load each manifest YAML file and assert that required fields
are present and set to the expected values, without requiring a live cluster.

Requirements: 5.1–5.3, 6.1–6.4, 7.1–7.3, 8.1–8.4, 9.1–9.2,
              10.1–10.6, 11.1–11.2, 12.1–12.4, 13.2
"""
from pathlib import Path

import pytest
import yaml

# Resolve the k8s/ directory relative to this test file's location.
# tests/smoke/test_manifests.py  → up two levels → workspace root → k8s/
K8S_DIR = Path(__file__).parent.parent.parent / "k8s"


def load_manifest(filename: str) -> dict:
    """Load a single-document YAML manifest from the k8s/ directory."""
    path = K8S_DIR / filename
    with open(path) as fh:
        return yaml.safe_load(fh)


# ---------------------------------------------------------------------------
# namespace.yaml
# Requirements: 5.1, 5.2
# ---------------------------------------------------------------------------

class TestNamespaceManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("namespace.yaml")

    def test_kind_is_namespace(self, manifest):
        """Kind must be Namespace (Requirement 5.1)."""
        assert manifest["kind"] == "Namespace"

    def test_name_is_flask_mongodb_ns(self, manifest):
        """Namespace name must be flask-mongodb-ns (Requirement 5.1)."""
        assert manifest["metadata"]["name"] == "flask-mongodb-ns"

    def test_label_project(self, manifest):
        """Label project: flask-mongodb-k8s must be present (Requirement 5.2)."""
        labels = manifest["metadata"]["labels"]
        assert labels.get("project") == "flask-mongodb-k8s"

    def test_label_env(self, manifest):
        """Label env: demo must be present (Requirement 5.2)."""
        labels = manifest["metadata"]["labels"]
        assert labels.get("env") == "demo"


# ---------------------------------------------------------------------------
# mongo-secret.yaml
# Requirements: 6.1, 6.2
# ---------------------------------------------------------------------------

class TestMongoSecretManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("mongo-secret.yaml")

    def test_kind_is_secret(self, manifest):
        """Kind must be Secret (Requirement 6.1)."""
        assert manifest["kind"] == "Secret"

    def test_type_is_opaque(self, manifest):
        """Secret type must be Opaque (Requirement 6.1)."""
        assert manifest["type"] == "Opaque"

    def test_mongo_username_key_present(self, manifest):
        """mongo-username key must be present in secret data (Requirement 6.2)."""
        assert "mongo-username" in manifest["data"]

    def test_mongo_password_key_present(self, manifest):
        """mongo-password key must be present in secret data (Requirement 6.2)."""
        assert "mongo-password" in manifest["data"]

    def test_mongo_username_base64_value(self, manifest):
        """mongo-username must be base64('admin') = YWRtaW4= (Requirement 6.2)."""
        assert manifest["data"]["mongo-username"] == "YWRtaW4="

    def test_mongo_password_base64_value(self, manifest):
        """mongo-password must be base64('password') = cGFzc3dvcmQ= (Requirement 6.2)."""
        assert manifest["data"]["mongo-password"] == "cGFzc3dvcmQ="


# ---------------------------------------------------------------------------
# pv.yaml
# Requirements: 7.1
# ---------------------------------------------------------------------------

class TestPersistentVolumeManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("pv.yaml")

    def test_kind_is_persistent_volume(self, manifest):
        """Kind must be PersistentVolume (Requirement 7.1)."""
        assert manifest["kind"] == "PersistentVolume"

    def test_capacity_1gi(self, manifest):
        """PV capacity must be 1Gi (Requirement 7.1)."""
        assert manifest["spec"]["capacity"]["storage"] == "1Gi"

    def test_access_modes_contains_read_write_once(self, manifest):
        """accessModes must contain ReadWriteOnce (Requirement 7.1)."""
        assert "ReadWriteOnce" in manifest["spec"]["accessModes"]

    def test_storage_class_name_manual(self, manifest):
        """storageClassName must be manual (Requirement 7.1)."""
        assert manifest["spec"]["storageClassName"] == "manual"

    def test_host_path(self, manifest):
        """hostPath.path must be /mnt/data/mongodb (Requirement 7.1)."""
        assert manifest["spec"]["hostPath"]["path"] == "/mnt/data/mongodb"


# ---------------------------------------------------------------------------
# pvc.yaml
# Requirements: 7.2
# ---------------------------------------------------------------------------

class TestPersistentVolumeClaimManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("pvc.yaml")

    def test_kind_is_persistent_volume_claim(self, manifest):
        """Kind must be PersistentVolumeClaim (Requirement 7.2)."""
        assert manifest["kind"] == "PersistentVolumeClaim"

    def test_namespace_is_flask_mongodb_ns(self, manifest):
        """PVC must be in flask-mongodb-ns namespace (Requirement 7.2)."""
        assert manifest["metadata"]["namespace"] == "flask-mongodb-ns"

    def test_requests_storage_1gi(self, manifest):
        """PVC must request 1Gi of storage (Requirement 7.2)."""
        assert manifest["spec"]["resources"]["requests"]["storage"] == "1Gi"

    def test_storage_class_name_manual(self, manifest):
        """storageClassName must be manual to match PV (Requirement 7.2)."""
        assert manifest["spec"]["storageClassName"] == "manual"

    def test_access_modes_contains_read_write_once(self, manifest):
        """accessModes must contain ReadWriteOnce (Requirement 7.2)."""
        assert "ReadWriteOnce" in manifest["spec"]["accessModes"]


# ---------------------------------------------------------------------------
# mongodb-statefulset.yaml
# Requirements: 8.1, 8.2, 8.3, 8.4, 6.4, 7.3
# ---------------------------------------------------------------------------

class TestMongoDBStatefulSetManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("mongodb-statefulset.yaml")

    @pytest.fixture(scope="class")
    @classmethod
    def container(cls, manifest):
        """Return the first (and only) container spec."""
        return manifest["spec"]["template"]["spec"]["containers"][0]

    def test_kind_is_stateful_set(self, manifest):
        """Kind must be StatefulSet (Requirement 8.1)."""
        assert manifest["kind"] == "StatefulSet"

    def test_image_is_mongo_pinned(self, container):
        """MongoDB image must be a pinned mongo version (Requirement 8.1)."""
        assert container["image"] == "mongo:7.0.11"

    def test_resource_limit_cpu(self, container):
        """CPU limit must be 500m (Requirement 8.2)."""
        assert container["resources"]["limits"]["cpu"] == "500m"

    def test_resource_limit_memory(self, container):
        """Memory limit must be 512Mi (Requirement 8.2)."""
        assert container["resources"]["limits"]["memory"] == "512Mi"

    def test_readiness_probe_defined(self, container):
        """readinessProbe must be defined (Requirement 8.3)."""
        assert "readinessProbe" in container

    def test_env_username_uses_secret_key_ref(self, container):
        """MONGO_INITDB_ROOT_USERNAME env var must use secretKeyRef (Requirement 6.4)."""
        env_vars = {e["name"]: e for e in container["env"]}
        assert "MONGO_INITDB_ROOT_USERNAME" in env_vars
        assert "secretKeyRef" in env_vars["MONGO_INITDB_ROOT_USERNAME"]["valueFrom"]

    def test_env_password_uses_secret_key_ref(self, container):
        """MONGO_INITDB_ROOT_PASSWORD env var must use secretKeyRef (Requirement 6.4)."""
        env_vars = {e["name"]: e for e in container["env"]}
        assert "MONGO_INITDB_ROOT_PASSWORD" in env_vars
        assert "secretKeyRef" in env_vars["MONGO_INITDB_ROOT_PASSWORD"]["valueFrom"]


# ---------------------------------------------------------------------------
# flask-deployment.yaml
# Requirements: 10.1–10.6, 6.3
# ---------------------------------------------------------------------------

class TestFlaskDeploymentManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("flask-deployment.yaml")

    @pytest.fixture(scope="class")
    @classmethod
    def container(cls, manifest):
        """Return the first (and only) container spec."""
        return manifest["spec"]["template"]["spec"]["containers"][0]

    def test_kind_is_deployment(self, manifest):
        """Kind must be Deployment (Requirement 10.1)."""
        assert manifest["kind"] == "Deployment"

    def test_replicas_is_2(self, manifest):
        """Flask deployment must have 2 replicas (Requirement 10.1)."""
        assert manifest["spec"]["replicas"] == 2

    def test_resource_limit_cpu(self, container):
        """CPU limit must be 500m (Requirement 10.3)."""
        assert container["resources"]["limits"]["cpu"] == "500m"

    def test_resource_limit_memory(self, container):
        """Memory limit must be 512Mi (Requirement 10.3)."""
        assert container["resources"]["limits"]["memory"] == "512Mi"

    def test_readiness_probe_defined(self, container):
        """readinessProbe must be defined (Requirement 10.4)."""
        assert "readinessProbe" in container

    def test_liveness_probe_defined(self, container):
        """livenessProbe must be defined (Requirement 10.5)."""
        assert "livenessProbe" in container

    def test_env_mongo_username_uses_secret_key_ref(self, container):
        """MONGO_USERNAME env var must use secretKeyRef (Requirement 6.3, 10.6)."""
        env_vars = {e["name"]: e for e in container["env"]}
        assert "MONGO_USERNAME" in env_vars
        assert "secretKeyRef" in env_vars["MONGO_USERNAME"]["valueFrom"]

    def test_env_mongo_password_uses_secret_key_ref(self, container):
        """MONGO_PASSWORD env var must use secretKeyRef (Requirement 6.3, 10.6)."""
        env_vars = {e["name"]: e for e in container["env"]}
        assert "MONGO_PASSWORD" in env_vars
        assert "secretKeyRef" in env_vars["MONGO_PASSWORD"]["valueFrom"]


# ---------------------------------------------------------------------------
# flask-service.yaml
# Requirements: 11.1, 11.2
# ---------------------------------------------------------------------------

class TestFlaskServiceManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("flask-service.yaml")

    def test_kind_is_service(self, manifest):
        """Kind must be Service (Requirement 11.1)."""
        assert manifest["kind"] == "Service"

    def test_service_type_is_nodeport(self, manifest):
        """Flask service type must be NodePort (Requirement 11.1)."""
        assert manifest["spec"]["type"] == "NodePort"

    def test_target_port_is_5000(self, manifest):
        """targetPort must be 5000 (Requirement 11.2)."""
        ports = manifest["spec"]["ports"]
        target_ports = [p["targetPort"] for p in ports]
        assert 5000 in target_ports


# ---------------------------------------------------------------------------
# mongodb-service.yaml
# Requirements: 9.1, 9.2
# ---------------------------------------------------------------------------

class TestMongoDBServiceManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("mongodb-service.yaml")

    def test_kind_is_service(self, manifest):
        """Kind must be Service (Requirement 9.1)."""
        assert manifest["kind"] == "Service"

    def test_service_type_is_clusterip(self, manifest):
        """MongoDB service type must be ClusterIP (Requirement 9.1)."""
        assert manifest["spec"]["type"] == "ClusterIP"

    def test_port_is_27017(self, manifest):
        """MongoDB service port must be 27017 (Requirement 9.2)."""
        ports = manifest["spec"]["ports"]
        port_numbers = [p["port"] for p in ports]
        assert 27017 in port_numbers


# ---------------------------------------------------------------------------
# hpa.yaml
# Requirements: 12.1–12.4
# ---------------------------------------------------------------------------

class TestHPAManifest:
    @pytest.fixture(scope="class")
    @classmethod
    def manifest(cls):
        return load_manifest("hpa.yaml")

    def test_kind_is_hpa(self, manifest):
        """Kind must be HorizontalPodAutoscaler (Requirement 12.1)."""
        assert manifest["kind"] == "HorizontalPodAutoscaler"

    def test_api_version_is_autoscaling_v2(self, manifest):
        """HPA apiVersion must be autoscaling/v2 (Requirement 12.1)."""
        assert manifest["apiVersion"] == "autoscaling/v2"

    def test_min_replicas_is_2(self, manifest):
        """HPA minReplicas must be 2 (Requirement 12.2)."""
        assert manifest["spec"]["minReplicas"] == 2

    def test_max_replicas_is_5(self, manifest):
        """HPA maxReplicas must be 5 (Requirement 12.3)."""
        assert manifest["spec"]["maxReplicas"] == 5

    def test_cpu_utilization_target_is_70(self, manifest):
        """HPA CPU averageUtilization target must be 70 (Requirement 12.4)."""
        metrics = manifest["spec"]["metrics"]
        cpu_metrics = [
            m for m in metrics
            if m.get("type") == "Resource"
            and m.get("resource", {}).get("name") == "cpu"
        ]
        assert cpu_metrics, "No CPU resource metric found in HPA spec"
        cpu_target = cpu_metrics[0]["resource"]["target"]
        assert cpu_target["averageUtilization"] == 70
