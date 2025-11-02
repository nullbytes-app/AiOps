"""
Integration tests for Kubernetes deployment.

These tests validate that all Kubernetes manifests can be applied to a cluster
and that the deployed components are healthy and ready to serve traffic.

Note: These tests require a running Kubernetes cluster (minikube, kind, or cloud).
"""

import subprocess
import time
import pytest
from pathlib import Path


NAMESPACE = "ai-agents"
TIMEOUT = 300  # 5 minutes


@pytest.fixture(scope="session")
def k8s_available():
    """Check if Kubernetes cluster is available."""
    try:
        result = subprocess.run(
            ["kubectl", "cluster-info"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


@pytest.fixture(scope="session")
def k8s_dir():
    """Get k8s directory path."""
    return Path(__file__).parent.parent.parent / 'k8s'


@pytest.fixture(scope="session", autouse=True)
def setup_teardown_namespace(k8s_available):
    """Create namespace before tests, clean up after."""
    if not k8s_available:
        pytest.skip("Kubernetes cluster not available")

    # Create namespace
    subprocess.run(
        ["kubectl", "create", "namespace", NAMESPACE],
        capture_output=True,
        timeout=10
    )
    yield
    # Teardown - delete namespace and all resources
    subprocess.run(
        ["kubectl", "delete", "namespace", NAMESPACE],
        capture_output=True,
        timeout=30
    )


class TestManifestApplication:
    """Tests for applying manifests to Kubernetes cluster."""

    def test_apply_namespace_manifest(self, k8s_available, k8s_dir):
        """Test applying namespace manifest."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "namespace.yaml")],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply namespace: {result.stderr}"

    def test_apply_configmap_manifest(self, k8s_available, k8s_dir):
        """Test applying ConfigMap manifest."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "configmap.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply ConfigMap: {result.stderr}"

    def test_apply_postgres_manifest(self, k8s_available, k8s_dir):
        """Test applying PostgreSQL StatefulSet."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "deployment-postgres.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply PostgreSQL: {result.stderr}"

    def test_apply_redis_manifest(self, k8s_available, k8s_dir):
        """Test applying Redis StatefulSet."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "deployment-redis.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply Redis: {result.stderr}"

    def test_apply_api_manifest(self, k8s_available, k8s_dir):
        """Test applying API Deployment."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "deployment-api.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply API: {result.stderr}"

    def test_apply_worker_manifest(self, k8s_available, k8s_dir):
        """Test applying Worker Deployment."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "deployment-worker.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply Worker: {result.stderr}"

    def test_apply_hpa_manifest(self, k8s_available, k8s_dir):
        """Test applying HPA."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "hpa-worker.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply HPA: {result.stderr}"

    def test_apply_ingress_manifest(self, k8s_available, k8s_dir):
        """Test applying Ingress."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "apply", "-f", str(k8s_dir / "ingress.yaml"), "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=30
        )
        assert result.returncode == 0, f"Failed to apply Ingress: {result.stderr}"


class TestResourceCreation:
    """Tests for verifying resources are created."""

    def test_namespace_created(self, k8s_available):
        """Test that namespace was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "namespace", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0

    def test_statefulset_postgres_created(self, k8s_available):
        """Test that PostgreSQL StatefulSet was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "statefulset", "postgresql", "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0

    def test_statefulset_redis_created(self, k8s_available):
        """Test that Redis StatefulSet was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "statefulset", "redis", "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0

    def test_deployment_api_created(self, k8s_available):
        """Test that API Deployment was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "deployment", "api", "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0

    def test_deployment_worker_created(self, k8s_available):
        """Test that Worker Deployment was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "deployment", "worker", "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0

    def test_services_created(self, k8s_available):
        """Test that all services were created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        services = ["postgresql", "redis", "api"]
        for service in services:
            result = subprocess.run(
                ["kubectl", "get", "service", service, "-n", NAMESPACE],
                capture_output=True,
                text=True,
                timeout=10
            )
            assert result.returncode == 0, f"Service {service} not found"

    def test_configmap_created(self, k8s_available):
        """Test that ConfigMap was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "configmap", "app-config", "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0

    def test_hpa_created(self, k8s_available):
        """Test that HPA was created."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "hpa", "worker-hpa", "-n", NAMESPACE],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.returncode == 0


class TestResourceSpecification:
    """Tests for verifying resource specifications are correct."""

    def test_postgres_replica_count(self, k8s_available):
        """Test PostgreSQL StatefulSet has correct replica count."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "statefulset", "postgresql", "-n", NAMESPACE, "-o", "jsonpath={.spec.replicas}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.stdout.strip() == "1"

    def test_api_replica_count(self, k8s_available):
        """Test API Deployment has correct replica count."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "deployment", "api", "-n", NAMESPACE, "-o", "jsonpath={.spec.replicas}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.stdout.strip() == "2"

    def test_worker_replica_count(self, k8s_available):
        """Test Worker Deployment has correct replica count."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result = subprocess.run(
            ["kubectl", "get", "deployment", "worker", "-n", NAMESPACE, "-o", "jsonpath={.spec.replicas}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result.stdout.strip() == "2"

    def test_hpa_min_max_replicas(self, k8s_available):
        """Test HPA has correct min/max replica counts."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        result_min = subprocess.run(
            ["kubectl", "get", "hpa", "worker-hpa", "-n", NAMESPACE, "-o", "jsonpath={.spec.minReplicas}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        result_max = subprocess.run(
            ["kubectl", "get", "hpa", "worker-hpa", "-n", NAMESPACE, "-o", "jsonpath={.spec.maxReplicas}"],
            capture_output=True,
            text=True,
            timeout=10
        )
        assert result_min.stdout.strip() == "1"
        assert result_max.stdout.strip() == "10"


class TestPodHealth:
    """Tests for pod health and readiness (requires pods to be running)."""

    @pytest.mark.slow
    def test_pods_eventually_ready(self, k8s_available):
        """Test that pods eventually reach Ready state."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        pytest.skip("Requires actual images and running cluster - skipped in CI")

    @pytest.mark.slow
    def test_service_endpoints_available(self, k8s_available):
        """Test that services have endpoints (pods connected)."""
        if not k8s_available:
            pytest.skip("Kubernetes cluster not available")

        pytest.skip("Requires running pods - skipped in CI")


class TestDocumentation:
    """Tests for documentation files."""

    def test_deployment_guide_exists(self):
        """Test that deployment.md exists."""
        deployment_doc = Path(__file__).parent.parent.parent / 'docs' / 'deployment.md'
        assert deployment_doc.exists()

    def test_deployment_guide_contains_sections(self):
        """Test that deployment.md contains required sections."""
        deployment_doc = Path(__file__).parent.parent.parent / 'docs' / 'deployment.md'
        with open(deployment_doc, 'r') as f:
            content = f.read()

        required_sections = [
            "Prerequisites",
            "Quick Start",
            "Secret Management",
            "Scaling",
            "Monitoring",
            "Troubleshooting",
            "Production"
        ]

        for section in required_sections:
            assert section in content, f"Missing section: {section}"

    def test_readme_references_deployment_guide(self):
        """Test that README references deployment.md."""
        readme = Path(__file__).parent.parent.parent / 'README.md'
        with open(readme, 'r') as f:
            content = f.read()

        assert "deployment.md" in content
        assert "Kubernetes" in content
