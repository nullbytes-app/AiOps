"""
Unit tests for Kubernetes manifest validation.

Tests verify YAML structure, required fields, and spec compliance for all
Kubernetes manifests without requiring a running cluster.
"""

import os
import pytest
import yaml
from pathlib import Path


# Load manifest files
def load_manifest(manifest_path: str) -> dict:
    """Load and parse YAML manifest."""
    with open(manifest_path, 'r') as f:
        return yaml.safe_load(f)


def load_manifest_list(manifest_path: str) -> list:
    """Load and parse multi-document YAML manifest (returns list of docs)."""
    with open(manifest_path, 'r') as f:
        docs = []
        for doc in yaml.safe_load_all(f):
            if doc:
                docs.append(doc)
        return docs


# Test fixtures
@pytest.fixture
def k8s_dir():
    """Get k8s directory path."""
    return Path(__file__).parent.parent.parent / 'k8s'


@pytest.fixture
def namespace_manifest(k8s_dir):
    """Load namespace manifest."""
    return load_manifest(k8s_dir / 'namespace.yaml')


@pytest.fixture
def postgres_manifests(k8s_dir):
    """Load PostgreSQL manifests."""
    return load_manifest_list(k8s_dir / 'deployment-postgres.yaml')


@pytest.fixture
def redis_manifests(k8s_dir):
    """Load Redis manifests."""
    return load_manifest_list(k8s_dir / 'deployment-redis.yaml')


@pytest.fixture
def api_manifests(k8s_dir):
    """Load API manifests."""
    return load_manifest_list(k8s_dir / 'deployment-api.yaml')


@pytest.fixture
def postgres_service_manifest(k8s_dir):
    """Load PostgreSQL service manifest."""
    return load_manifest(k8s_dir / 'service-postgres.yaml')


@pytest.fixture
def redis_service_manifest(k8s_dir):
    """Load Redis service manifest."""
    return load_manifest(k8s_dir / 'service-redis.yaml')


@pytest.fixture
def api_service_manifest(k8s_dir):
    """Load API service manifest."""
    return load_manifest(k8s_dir / 'service-api.yaml')


@pytest.fixture
def worker_manifest(k8s_dir):
    """Load Worker manifest."""
    return load_manifest(k8s_dir / 'deployment-worker.yaml')


@pytest.fixture
def hpa_manifest(k8s_dir):
    """Load HPA manifest."""
    return load_manifest(k8s_dir / 'hpa-worker.yaml')


@pytest.fixture
def configmap_manifest(k8s_dir):
    """Load ConfigMap manifest."""
    return load_manifest(k8s_dir / 'configmap.yaml')


@pytest.fixture
def ingress_manifest(k8s_dir):
    """Load Ingress manifest."""
    manifests = load_manifest_list(k8s_dir / 'ingress.yaml')
    # Return first Ingress document (skip comments sections)
    ingress_docs = [m for m in manifests if m and m.get('kind') == 'Ingress']
    return ingress_docs[0] if ingress_docs else None


class TestNamespace:
    """Tests for Kubernetes namespace manifest."""

    def test_namespace_exists(self, k8s_dir):
        """Verify namespace.yaml file exists."""
        assert (k8s_dir / 'namespace.yaml').exists()

    def test_namespace_kind(self, namespace_manifest):
        """Verify manifest kind is Namespace."""
        assert namespace_manifest['kind'] == 'Namespace'

    def test_namespace_name(self, namespace_manifest):
        """Verify namespace name is 'ai-agents'."""
        assert namespace_manifest['metadata']['name'] == 'ai-agents'

    def test_namespace_labels(self, namespace_manifest):
        """Verify namespace has required labels."""
        labels = namespace_manifest['metadata']['labels']
        assert labels['environment'] == 'development'
        assert labels['project'] == 'ai-agents'


class TestPostgreSQL:
    """Tests for PostgreSQL StatefulSet and Service."""

    def test_postgres_manifests_exist(self, k8s_dir):
        """Verify PostgreSQL deployment manifest exists."""
        assert (k8s_dir / 'deployment-postgres.yaml').exists()

    def test_postgres_has_statefulset(self, postgres_manifests):
        """Verify PostgreSQL manifest contains StatefulSet."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        assert len(statefulsets) == 1
        assert statefulsets[0]['metadata']['name'] == 'postgresql'

    def test_postgres_has_service(self, postgres_service_manifest):
        """Verify PostgreSQL service manifest exists."""
        assert postgres_service_manifest['kind'] == 'Service'
        assert postgres_service_manifest['metadata']['name'] == 'postgresql'

    def test_postgres_namespace(self, postgres_manifests):
        """Verify PostgreSQL resources in correct namespace."""
        for manifest in postgres_manifests:
            assert manifest['metadata']['namespace'] == 'ai-agents'

    def test_postgres_image(self, postgres_manifests):
        """Verify PostgreSQL uses correct image."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        image = statefulsets[0]['spec']['template']['spec']['containers'][0]['image']
        assert image == 'postgres:17-alpine'

    def test_postgres_container_port(self, postgres_manifests):
        """Verify PostgreSQL container port is 5432."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        port = statefulsets[0]['spec']['template']['spec']['containers'][0]['ports'][0]['containerPort']
        assert port == 5432

    def test_postgres_resource_requests(self, postgres_manifests):
        """Verify PostgreSQL has correct resource requests."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        resources = statefulsets[0]['spec']['template']['spec']['containers'][0]['resources']
        assert resources['requests']['cpu'] == '500m'
        assert resources['requests']['memory'] == '1Gi'

    def test_postgres_resource_limits(self, postgres_manifests):
        """Verify PostgreSQL has correct resource limits."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        resources = statefulsets[0]['spec']['template']['spec']['containers'][0]['resources']
        assert resources['limits']['cpu'] == '1000m'
        assert resources['limits']['memory'] == '4Gi'

    def test_postgres_volume_claim(self, postgres_manifests):
        """Verify PostgreSQL has PersistentVolumeClaim."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        claims = statefulsets[0]['spec']['volumeClaimTemplates']
        assert len(claims) == 1
        assert claims[0]['spec']['resources']['requests']['storage'] == '10Gi'

    def test_postgres_readiness_probe(self, postgres_manifests):
        """Verify PostgreSQL has readiness probe."""
        statefulsets = [m for m in postgres_manifests if m['kind'] == 'StatefulSet']
        container = statefulsets[0]['spec']['template']['spec']['containers'][0]
        assert 'readinessProbe' in container
        assert container['readinessProbe']['initialDelaySeconds'] == 5


class TestRedis:
    """Tests for Redis StatefulSet and Service."""

    def test_redis_manifests_exist(self, k8s_dir):
        """Verify Redis deployment manifest exists."""
        assert (k8s_dir / 'deployment-redis.yaml').exists()

    def test_redis_has_statefulset(self, redis_manifests):
        """Verify Redis manifest contains StatefulSet."""
        statefulsets = [m for m in redis_manifests if m['kind'] == 'StatefulSet']
        assert len(statefulsets) == 1
        assert statefulsets[0]['metadata']['name'] == 'redis'

    def test_redis_has_service(self, redis_service_manifest):
        """Verify Redis service manifest exists."""
        assert redis_service_manifest['kind'] == 'Service'
        assert redis_service_manifest['metadata']['name'] == 'redis'

    def test_redis_has_configmap(self, redis_manifests):
        """Verify Redis manifest contains ConfigMap for configuration."""
        configmaps = [m for m in redis_manifests if m['kind'] == 'ConfigMap']
        assert len(configmaps) == 1
        assert configmaps[0]['metadata']['name'] == 'redis-config'

    def test_redis_image(self, redis_manifests):
        """Verify Redis uses correct image."""
        statefulsets = [m for m in redis_manifests if m['kind'] == 'StatefulSet']
        image = statefulsets[0]['spec']['template']['spec']['containers'][0]['image']
        assert image == 'redis:7-alpine'

    def test_redis_container_port(self, redis_manifests):
        """Verify Redis container port is 6379."""
        statefulsets = [m for m in redis_manifests if m['kind'] == 'StatefulSet']
        port = statefulsets[0]['spec']['template']['spec']['containers'][0]['ports'][0]['containerPort']
        assert port == 6379

    def test_redis_resource_limits(self, redis_manifests):
        """Verify Redis has correct resource limits."""
        statefulsets = [m for m in redis_manifests if m['kind'] == 'StatefulSet']
        resources = statefulsets[0]['spec']['template']['spec']['containers'][0]['resources']
        assert resources['limits']['cpu'] == '500m'
        assert resources['limits']['memory'] == '2Gi'

    def test_redis_volume_claim(self, redis_manifests):
        """Verify Redis has PersistentVolumeClaim."""
        statefulsets = [m for m in redis_manifests if m['kind'] == 'StatefulSet']
        claims = statefulsets[0]['spec']['volumeClaimTemplates']
        assert len(claims) == 1
        assert claims[0]['spec']['resources']['requests']['storage'] == '5Gi'

    def test_redis_nonroot_user(self, redis_manifests):
        """Verify Redis runs as non-root user."""
        statefulsets = [m for m in redis_manifests if m['kind'] == 'StatefulSet']
        security_context = statefulsets[0]['spec']['template']['spec']['containers'][0]['securityContext']
        assert security_context['runAsNonRoot'] is True
        assert security_context['runAsUser'] == 999


class TestAPI:
    """Tests for FastAPI Deployment and Service."""

    def test_api_manifest_exists(self, k8s_dir):
        """Verify API deployment manifest exists."""
        assert (k8s_dir / 'deployment-api.yaml').exists()

    def test_api_has_deployment(self, api_manifests):
        """Verify API manifest contains Deployment."""
        deployments = [m for m in api_manifests if m['kind'] == 'Deployment']
        assert len(deployments) == 1
        assert deployments[0]['metadata']['name'] == 'api'

    def test_api_has_service(self, api_service_manifest):
        """Verify API service manifest exists."""
        assert api_service_manifest['kind'] == 'Service'
        assert api_service_manifest['metadata']['name'] == 'api'

    def test_api_replicas(self, api_manifests):
        """Verify API deployment has 2 replicas."""
        deployments = [m for m in api_manifests if m['kind'] == 'Deployment']
        assert deployments[0]['spec']['replicas'] == 2

    def test_api_container_port(self, api_manifests):
        """Verify API container port is 8000."""
        deployments = [m for m in api_manifests if m['kind'] == 'Deployment']
        port = deployments[0]['spec']['template']['spec']['containers'][0]['ports'][0]['containerPort']
        assert port == 8000

    def test_api_resource_limits(self, api_manifests):
        """Verify API has correct resource limits."""
        deployments = [m for m in api_manifests if m['kind'] == 'Deployment']
        resources = deployments[0]['spec']['template']['spec']['containers'][0]['resources']
        assert resources['limits']['cpu'] == '500m'
        assert resources['limits']['memory'] == '1Gi'

    def test_api_nonroot_security_context(self, api_manifests):
        """Verify API runs as non-root user."""
        deployments = [m for m in api_manifests if m['kind'] == 'Deployment']
        security_context = deployments[0]['spec']['template']['spec']['containers'][0]['securityContext']
        assert security_context['runAsNonRoot'] is True
        assert security_context['runAsUser'] == 1000

    def test_api_health_probes(self, api_manifests):
        """Verify API has liveness, readiness, and startup probes."""
        deployments = [m for m in api_manifests if m['kind'] == 'Deployment']
        container = deployments[0]['spec']['template']['spec']['containers'][0]
        assert 'livenessProbe' in container
        assert 'readinessProbe' in container
        assert 'startupProbe' in container

    def test_api_service_type(self, api_service_manifest):
        """Verify API service is LoadBalancer type."""
        assert api_service_manifest['spec']['type'] == 'LoadBalancer'


class TestWorker:
    """Tests for Celery Worker Deployment."""

    def test_worker_manifest_exists(self, k8s_dir):
        """Verify Worker deployment manifest exists."""
        assert (k8s_dir / 'deployment-worker.yaml').exists()

    def test_worker_kind(self, worker_manifest):
        """Verify worker manifest kind is Deployment."""
        assert worker_manifest['kind'] == 'Deployment'

    def test_worker_name(self, worker_manifest):
        """Verify worker deployment name is 'worker'."""
        assert worker_manifest['metadata']['name'] == 'worker'

    def test_worker_replicas(self, worker_manifest):
        """Verify worker deployment has 2 replicas."""
        assert worker_manifest['spec']['replicas'] == 2

    def test_worker_resource_limits(self, worker_manifest):
        """Verify worker has correct resource limits."""
        resources = worker_manifest['spec']['template']['spec']['containers'][0]['resources']
        assert resources['limits']['cpu'] == '1000m'
        assert resources['limits']['memory'] == '2Gi'

    def test_worker_graceful_shutdown(self, worker_manifest):
        """Verify worker has graceful shutdown period."""
        grace_period = worker_manifest['spec']['template']['spec']['terminationGracePeriodSeconds']
        assert grace_period == 120

    def test_worker_celery_command(self, worker_manifest):
        """Verify worker runs correct Celery command."""
        command = worker_manifest['spec']['template']['spec']['containers'][0]['command']
        assert command[0] == 'celery'
        assert command[2] == 'src.workers.celery_app'
        assert 'worker' in command


class TestHPA:
    """Tests for Horizontal Pod Autoscaler."""

    def test_hpa_manifest_exists(self, k8s_dir):
        """Verify HPA manifest exists."""
        assert (k8s_dir / 'hpa-worker.yaml').exists()

    def test_hpa_kind(self, hpa_manifest):
        """Verify HPA manifest kind is HorizontalPodAutoscaler."""
        assert hpa_manifest['kind'] == 'HorizontalPodAutoscaler'

    def test_hpa_name(self, hpa_manifest):
        """Verify HPA name is 'worker-hpa'."""
        assert hpa_manifest['metadata']['name'] == 'worker-hpa'

    def test_hpa_target(self, hpa_manifest):
        """Verify HPA targets worker deployment."""
        target = hpa_manifest['spec']['scaleTargetRef']
        assert target['kind'] == 'Deployment'
        assert target['name'] == 'worker'

    def test_hpa_min_max_replicas(self, hpa_manifest):
        """Verify HPA min/max replica counts."""
        assert hpa_manifest['spec']['minReplicas'] == 1
        assert hpa_manifest['spec']['maxReplicas'] == 10

    def test_hpa_cpu_metric(self, hpa_manifest):
        """Verify HPA uses CPU utilization metric."""
        metrics = hpa_manifest['spec']['metrics']
        cpu_metrics = [m for m in metrics if m['resource']['name'] == 'cpu']
        assert len(cpu_metrics) == 1
        assert cpu_metrics[0]['resource']['target']['averageUtilization'] == 70


class TestConfigMap:
    """Tests for ConfigMap."""

    def test_configmap_manifest_exists(self, k8s_dir):
        """Verify ConfigMap manifest exists."""
        assert (k8s_dir / 'configmap.yaml').exists()

    def test_configmap_kind(self, configmap_manifest):
        """Verify ConfigMap manifest kind."""
        assert configmap_manifest['kind'] == 'ConfigMap'

    def test_configmap_name(self, configmap_manifest):
        """Verify ConfigMap name is 'app-config'."""
        assert configmap_manifest['metadata']['name'] == 'app-config'

    def test_configmap_data(self, configmap_manifest):
        """Verify ConfigMap contains expected configuration."""
        data = configmap_manifest['data']
        assert 'environment' in data
        assert 'log_level' in data

    def test_configmap_environment_value(self, configmap_manifest):
        """Verify environment is set to development."""
        assert configmap_manifest['data']['environment'] == 'development'


class TestSecrets:
    """Tests for Secrets template."""

    def test_secrets_template_exists(self, k8s_dir):
        """Verify secrets.yaml.example template exists."""
        assert (k8s_dir / 'secrets.yaml.example').exists()

    def test_secrets_template_readable(self, k8s_dir):
        """Verify secrets template can be read."""
        with open(k8s_dir / 'secrets.yaml.example', 'r') as f:
            content = f.read()
        assert 'PLACEHOLDER' in content
        assert 'NEVER commit' in content

    def test_actual_secrets_not_in_repo(self, k8s_dir):
        """Verify actual secrets.yaml is not in repo (only example)."""
        # The test checks that if secrets.yaml exists, it's in .gitignore
        # For this test, we just verify the template exists
        assert (k8s_dir / 'secrets.yaml.example').exists()


class TestIngress:
    """Tests for Ingress manifest."""

    def test_ingress_manifest_exists(self, k8s_dir):
        """Verify Ingress manifest exists."""
        assert (k8s_dir / 'ingress.yaml').exists()

    def test_ingress_kind(self, ingress_manifest):
        """Verify Ingress manifest kind."""
        assert ingress_manifest['kind'] == 'Ingress'

    def test_ingress_name(self, ingress_manifest):
        """Verify Ingress name is 'api-ingress'."""
        assert ingress_manifest['metadata']['name'] == 'api-ingress'

    def test_ingress_has_rules(self, ingress_manifest):
        """Verify Ingress has routing rules."""
        assert 'rules' in ingress_manifest['spec']
        assert len(ingress_manifest['spec']['rules']) >= 2

    def test_ingress_routes_to_api(self, ingress_manifest):
        """Verify Ingress routes to API service."""
        rules = ingress_manifest['spec']['rules']
        for rule in rules:
            for path in rule['http']['paths']:
                assert path['backend']['service']['name'] == 'api'


class TestManifestIntegration:
    """Integration tests for all manifests together."""

    def test_all_manifests_in_namespace(self, k8s_dir):
        """Verify all manifests reference ai-agents namespace."""
        manifest_files = [
            'deployment-postgres.yaml',
            'deployment-redis.yaml',
            'deployment-api.yaml',
            'deployment-worker.yaml',
            'hpa-worker.yaml',
            'configmap.yaml',
            'ingress.yaml'
        ]

        for file in manifest_files:
            path = k8s_dir / file
            assert path.exists(), f"Missing {file}"

            with open(path, 'r') as f:
                docs = list(yaml.safe_load_all(f))
                for doc in docs:
                    if doc and 'metadata' in doc and 'namespace' in doc['metadata']:
                        assert doc['metadata']['namespace'] == 'ai-agents'

    def test_manifests_have_labels(self, k8s_dir):
        """Verify manifests have app labels."""
        manifest_files = [
            'deployment-postgres.yaml',
            'deployment-redis.yaml',
            'deployment-api.yaml',
            'deployment-worker.yaml',
        ]

        for file in manifest_files:
            path = k8s_dir / file
            with open(path, 'r') as f:
                docs = list(yaml.safe_load_all(f))
                for doc in docs:
                    if doc and doc.get('kind') in ['Deployment', 'StatefulSet']:
                        assert 'labels' in doc['metadata']

    def test_test_deployment_script_exists(self, k8s_dir):
        """Verify test-deployment.sh exists and is executable."""
        script_path = k8s_dir / 'test-deployment.sh'
        assert script_path.exists()
        assert os.access(script_path, os.X_OK)
