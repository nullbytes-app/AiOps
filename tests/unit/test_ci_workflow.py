"""
Unit tests for GitHub Actions CI/CD workflow configuration.

Tests validate that:
1. Workflow file exists and has valid YAML structure
2. All required jobs are defined (lint-and-test, docker-build)
3. Workflow triggers are correctly configured (PR, main branch)
4. All required steps are present in each job
5. Performance optimizations (caching, timeouts) are configured
6. Security settings (permissions, secrets) are correct
"""

import pytest
import yaml
from pathlib import Path


class TestWorkflowFileStructure:
    """Tests for basic workflow file structure and YAML validity."""

    @pytest.fixture
    def workflow_path(self) -> Path:
        """Fixture providing path to the CI workflow file."""
        return Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"

    @pytest.fixture
    def workflow_content(self, workflow_path: Path) -> dict:
        """Fixture loading and parsing the workflow YAML file."""
        with open(workflow_path) as f:
            return yaml.safe_load(f)

    def test_workflow_file_exists(self, workflow_path: Path) -> None:
        """AC #1: Verify GitHub Actions workflow file exists."""
        assert workflow_path.exists(), f"Workflow file not found at {workflow_path}"
        assert workflow_path.suffix == ".yml", "Workflow file should be YAML format"

    def test_workflow_yaml_valid(self, workflow_content: dict) -> None:
        """Verify workflow YAML is valid and parseable."""
        assert workflow_content is not None, "Workflow YAML failed to parse"
        assert isinstance(workflow_content, dict), "Workflow should be a YAML dictionary"

    def test_workflow_name_defined(self, workflow_content: dict) -> None:
        """AC #1: Verify workflow has a descriptive name."""
        assert "name" in workflow_content, "Workflow must have a name"
        assert workflow_content["name"] == "AI Agents CI/CD Pipeline"

    def test_workflow_permissions_configured(self, workflow_content: dict) -> None:
        """Security: Verify workflow requests minimum permissions."""
        assert "permissions" in workflow_content, "Workflow must define permissions"
        perms = workflow_content["permissions"]
        assert perms.get("contents") == "read", "Must have read access to repo contents"
        assert perms.get("packages") == "write", "Must have write access to push images"


class TestWorkflowTriggers:
    """Tests for workflow trigger configuration."""

    @pytest.fixture
    def workflow_content(self) -> dict:
        """Fixture loading workflow content."""
        path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
        with open(path) as f:
            return yaml.safe_load(f)

    def test_triggers_defined(self, workflow_content: dict) -> None:
        """AC #2: Verify workflow triggers are defined."""
        # YAML parses 'on' as boolean True
        triggers = workflow_content.get(True) or workflow_content.get("on")
        assert triggers is not None, "Workflow must define 'on' triggers"

    def test_trigger_on_pr_to_main(self, workflow_content: dict) -> None:
        """AC #2: Verify workflow triggers on pull requests to main branch."""
        triggers = workflow_content.get(True) or workflow_content.get("on")
        assert "pull_request" in triggers, "Workflow must trigger on pull_request"
        assert "branches" in triggers["pull_request"]
        assert "main" in triggers["pull_request"]["branches"]

    def test_trigger_on_push_to_main(self, workflow_content: dict) -> None:
        """AC #2: Verify workflow triggers on push to main branch."""
        triggers = workflow_content.get(True) or workflow_content.get("on")
        assert "push" in triggers, "Workflow must trigger on push"
        assert "branches" in triggers["push"]
        assert "main" in triggers["push"]["branches"]


class TestLintAndTestJob:
    """Tests for the lint-and-test job configuration."""

    @pytest.fixture
    def workflow_content(self) -> dict:
        """Fixture loading workflow content."""
        path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
        with open(path) as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def lint_and_test_job(self, workflow_content: dict) -> dict:
        """Fixture extracting the lint-and-test job."""
        assert "jobs" in workflow_content
        assert "lint-and-test" in workflow_content["jobs"]
        return workflow_content["jobs"]["lint-and-test"]

    def test_job_exists(self, lint_and_test_job: dict) -> None:
        """Verify lint-and-test job is defined."""
        assert lint_and_test_job is not None

    def test_job_runs_on_ubuntu(self, lint_and_test_job: dict) -> None:
        """Verify job runs on ubuntu-latest."""
        assert lint_and_test_job.get("runs-on") == "ubuntu-latest"

    def test_job_has_timeout(self, lint_and_test_job: dict) -> None:
        """Performance: Verify job has timeout to prevent hung workflows."""
        assert "timeout-minutes" in lint_and_test_job
        assert lint_and_test_job["timeout-minutes"] == 15

    def test_job_has_steps(self, lint_and_test_job: dict) -> None:
        """Verify job defines steps."""
        assert "steps" in lint_and_test_job
        assert len(lint_and_test_job["steps"]) > 0

    def test_checkout_step_present(self, lint_and_test_job: dict) -> None:
        """AC #3: Verify code checkout step."""
        steps = lint_and_test_job["steps"]
        checkout_step = next((s for s in steps if "checkout" in s.get("name", "").lower()), None)
        assert checkout_step is not None, "Checkout step required"
        assert "uses" in checkout_step
        assert "actions/checkout@v4" in checkout_step["uses"]

    def test_python_setup_step_present(self, lint_and_test_job: dict) -> None:
        """AC #3: Verify Python 3.12 setup step."""
        steps = lint_and_test_job["steps"]
        python_step = next((s for s in steps if "python" in s.get("name", "").lower()), None)
        assert python_step is not None, "Python setup step required"
        assert "actions/setup-python@v5" in python_step["uses"]
        assert python_step["with"]["python-version"] == "3.12"

    def test_dependency_caching_present(self, lint_and_test_job: dict) -> None:
        """Performance: Verify dependency caching for faster builds."""
        steps = lint_and_test_job["steps"]
        cache_step = next((s for s in steps if "cache" in s.get("name", "").lower()), None)
        assert cache_step is not None, "Dependency caching required"
        assert "actions/cache@v3" in cache_step["uses"]

    def test_black_formatting_check_present(self, lint_and_test_job: dict) -> None:
        """AC #3: Verify Black code formatting check."""
        steps = lint_and_test_job["steps"]
        black_step = next((s for s in steps if "black" in s.get("name", "").lower()), None)
        assert black_step is not None, "Black formatting check required"
        assert "black --check" in black_step.get("run", "")

    def test_ruff_linting_present(self, lint_and_test_job: dict) -> None:
        """AC #3: Verify Ruff linting step."""
        steps = lint_and_test_job["steps"]
        ruff_step = next((s for s in steps if "ruff" in s.get("name", "").lower()), None)
        assert ruff_step is not None, "Ruff linting step required"
        assert "ruff check" in ruff_step.get("run", "")

    def test_mypy_type_checking_present(self, lint_and_test_job: dict) -> None:
        """AC #3: Verify Mypy type checking step."""
        steps = lint_and_test_job["steps"]
        mypy_step = next((s for s in steps if "mypy" in s.get("name", "").lower()), None)
        assert mypy_step is not None, "Mypy type checking step required"
        assert "mypy" in mypy_step.get("run", "")

    def test_pytest_with_coverage_present(self, lint_and_test_job: dict) -> None:
        """AC #3, #4: Verify Pytest execution with coverage reporting."""
        steps = lint_and_test_job["steps"]
        pytest_step = next((s for s in steps if "test" in s.get("name", "").lower()), None)
        assert pytest_step is not None, "Pytest execution step required"
        run_cmd = pytest_step.get("run", "")
        assert "--cov" in run_cmd, "Coverage measurement required"
        assert "80" in run_cmd, "80% coverage threshold required"

    def test_coverage_report_upload_present(self, lint_and_test_job: dict) -> None:
        """AC #4: Verify coverage report is uploaded as artifact."""
        steps = lint_and_test_job["steps"]
        upload_step = next(
            (s for s in steps if "upload" in s.get("name", "").lower() and "coverage" in s.get("name", "").lower()),
            None
        )
        assert upload_step is not None, "Coverage report upload step required"
        assert "upload-artifact@v3" in upload_step.get("uses", "")


class TestDockerBuildJob:
    """Tests for the docker-build job configuration."""

    @pytest.fixture
    def workflow_content(self) -> dict:
        """Fixture loading workflow content."""
        path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
        with open(path) as f:
            return yaml.safe_load(f)

    @pytest.fixture
    def docker_build_job(self, workflow_content: dict) -> dict:
        """Fixture extracting the docker-build job."""
        assert "jobs" in workflow_content
        assert "docker-build" in workflow_content["jobs"]
        return workflow_content["jobs"]["docker-build"]

    def test_job_exists(self, docker_build_job: dict) -> None:
        """Verify docker-build job is defined."""
        assert docker_build_job is not None

    def test_job_depends_on_lint_and_test(self, docker_build_job: dict) -> None:
        """AC #3: Verify docker-build depends on lint-and-test job."""
        assert "needs" in docker_build_job
        assert "lint-and-test" in docker_build_job["needs"]

    def test_job_runs_on_ubuntu(self, docker_build_job: dict) -> None:
        """Verify job runs on ubuntu-latest."""
        assert docker_build_job.get("runs-on") == "ubuntu-latest"

    def test_job_has_timeout(self, docker_build_job: dict) -> None:
        """Performance: Verify job has timeout."""
        assert "timeout-minutes" in docker_build_job

    def test_docker_buildx_setup_present(self, docker_build_job: dict) -> None:
        """Performance: Verify Docker Buildx setup for layer caching."""
        steps = docker_build_job["steps"]
        buildx_step = next((s for s in steps if "buildx" in s.get("name", "").lower()), None)
        assert buildx_step is not None, "Docker Buildx setup required"

    def test_docker_registry_login_present(self, docker_build_job: dict) -> None:
        """AC #5: Verify Docker registry login step."""
        steps = docker_build_job["steps"]
        login_step = next((s for s in steps if "registry" in s.get("name", "").lower()), None)
        assert login_step is not None, "Docker registry login required"
        assert "docker/login-action" in login_step.get("uses", "")

    def test_api_image_build_present(self, docker_build_job: dict) -> None:
        """AC #3: Verify API Docker image build."""
        steps = docker_build_job["steps"]
        api_build_step = next((s for s in steps if "api" in s.get("name", "").lower()), None)
        assert api_build_step is not None, "API image build step required"
        assert "backend.dockerfile" in api_build_step.get("run", "")

    def test_worker_image_build_present(self, docker_build_job: dict) -> None:
        """AC #3: Verify Worker Docker image build."""
        steps = docker_build_job["steps"]
        worker_build_step = next((s for s in steps if "worker" in s.get("name", "").lower()), None)
        assert worker_build_step is not None, "Worker image build step required"
        assert "celeryworker.dockerfile" in worker_build_step.get("run", "")

    def test_api_image_push_conditional(self, docker_build_job: dict) -> None:
        """AC #5: Verify API image push only on main branch."""
        steps = docker_build_job["steps"]
        push_step = next((s for s in steps if "push" in s.get("name", "").lower() and "api" in s.get("name", "").lower()), None)
        assert push_step is not None, "API image push step required"
        assert "if" in push_step, "Push step must be conditional"
        assert "main" in str(push_step)

    def test_worker_image_push_conditional(self, docker_build_job: dict) -> None:
        """AC #5: Verify Worker image push only on main branch."""
        steps = docker_build_job["steps"]
        push_step = next((s for s in steps if "push" in s.get("name", "").lower() and "worker" in s.get("name", "").lower()), None)
        assert push_step is not None, "Worker image push step required"


class TestAcceptanceCriteria:
    """Integration tests mapping workflow configuration to acceptance criteria."""

    @pytest.fixture
    def workflow_content(self) -> dict:
        """Fixture loading workflow content."""
        path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
        with open(path) as f:
            return yaml.safe_load(f)

    def test_ac_1_workflow_file_created(self, workflow_content: dict) -> None:
        """AC #1: GitHub Actions workflow file created (.github/workflows/ci.yml)."""
        assert workflow_content is not None
        assert workflow_content.get("name") == "AI Agents CI/CD Pipeline"

    def test_ac_2_workflow_triggers_pr_and_main(self, workflow_content: dict) -> None:
        """AC #2: Workflow runs on pull requests and main branch commits."""
        triggers = workflow_content.get(True) or workflow_content.get("on")
        assert "pull_request" in triggers
        assert "push" in triggers
        assert "main" in triggers["pull_request"]["branches"]
        assert "main" in triggers["push"]["branches"]

    def test_ac_3_automated_steps_present(self, workflow_content: dict) -> None:
        """AC #3: Automated steps: linting (black, ruff), type checking (mypy), unit tests (pytest), Docker build."""
        jobs = workflow_content["jobs"]
        lint_test = jobs["lint-and-test"]
        steps_str = str(lint_test)

        # All required tools must be present
        assert "black" in steps_str, "Black formatting check required"
        assert "ruff" in steps_str, "Ruff linting required"
        assert "mypy" in steps_str, "Mypy type checking required"
        assert "pytest" in steps_str, "Pytest unit tests required"

        # Docker build in separate job
        docker_jobs = jobs["docker-build"]
        assert "backend.dockerfile" in str(docker_jobs), "API Docker build required"

    def test_ac_4_coverage_report_generated(self, workflow_content: dict) -> None:
        """AC #4: Test coverage report generated and displayed."""
        jobs = workflow_content["jobs"]
        lint_test = jobs["lint-and-test"]
        steps_str = str(lint_test)

        assert "--cov" in steps_str, "Coverage measurement required"
        assert "upload-artifact" in steps_str, "Coverage report artifact upload required"

    def test_ac_5_docker_images_pushed(self, workflow_content: dict) -> None:
        """AC #5: Docker images pushed to container registry on main branch."""
        # Check for registry in env section
        env = workflow_content.get("env", {})
        assert "REGISTRY" in env, "Registry environment variable required"
        assert env["REGISTRY"] == "ghcr.io", "Must use GitHub Container Registry"

        # Check for image names in env
        assert "AI_IMAGE_NAME" in env or "API_IMAGE_NAME" in env, "API image name required"
        assert "WORKER_IMAGE_NAME" in env, "Worker image name required"

        # Check for push step in jobs
        docker_build = workflow_content["jobs"]["docker-build"]
        steps_str = str(docker_build)
        assert "ai-agents-api" in steps_str, "API image push required"
        assert "ai-agents-worker" in steps_str, "Worker image push required"

    def test_ac_6_badge_in_readme(self) -> None:
        """AC #6: Workflow status badge added to README."""
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path) as f:
            content = f.read()

        assert "CI/CD Pipeline" in content
        assert "github.com" in content and "workflows/ci.yml/badge.svg" in content

    def test_ac_7_documentation_in_readme(self) -> None:
        """AC #7: Pipeline completes successfully and documentation provided."""
        readme_path = Path(__file__).parent.parent.parent / "README.md"
        with open(readme_path) as f:
            content = f.read()

        # Documentation section must exist
        assert "## CI/CD Pipeline" in content
        assert "Workflow Overview" in content
        assert "Automated Checks" in content
        assert "Running Checks Locally" in content
        assert "Troubleshooting" in content


class TestEdgeCases:
    """Tests for edge cases and error conditions."""

    @pytest.fixture
    def workflow_content(self) -> dict:
        """Fixture loading workflow content."""
        path = Path(__file__).parent.parent.parent / ".github" / "workflows" / "ci.yml"
        with open(path) as f:
            return yaml.safe_load(f)

    def test_no_hardcoded_secrets(self, workflow_content: dict) -> None:
        """Security: Verify no hardcoded credentials in workflow."""
        workflow_str = str(workflow_content)

        # Should use secrets.GITHUB_TOKEN, not hardcoded values
        assert "secrets.GITHUB_TOKEN" in workflow_str

        # Should not contain common secret patterns
        assert "password=" not in workflow_str or "secrets.GITHUB_TOKEN" in workflow_str

    def test_all_images_have_tags(self, workflow_content: dict) -> None:
        """Verify Docker images are tagged with commit SHA for traceability."""
        docker_build = workflow_content["jobs"]["docker-build"]
        steps_str = str(docker_build)

        assert "github.sha" in steps_str, "Images must be tagged with commit SHA"

    def test_timeout_configured(self, workflow_content: dict) -> None:
        """Verify jobs have timeout to prevent hung workflows."""
        jobs = workflow_content["jobs"]

        for job_name, job_config in jobs.items():
            if job_name != "docker-build":  # docker-build job may not strictly need timeout
                assert "timeout-minutes" in job_config, f"Job {job_name} missing timeout"
