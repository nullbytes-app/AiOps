# Step 5: Code Quality and Security Review

Key observations (Kubernetes manifests and related code):

- [High] PostgreSQL container runs with `runAsNonRoot: false` (k8s/deployment-postgres.yaml:74), violating security constraint "All containers must run as non-root" from story context. Recommendation: set `runAsNonRoot: true` and `runAsUser: 999` (matches image user), add `fsGroup: 999` if needed for volume permissions.
- [Med] Service resources are embedded within deployment/statefulset manifests. While functional, tasks and file list specify separate `k8s/service-*.yaml` files. Recommendation: either split services into separate files for traceability or update story tasks/file list to reflect combined manifest approach.
- [Med] API image tag uses `latest` (k8s/deployment-api.yaml:31). For production readiness, pin to a version (e.g., `ai-agents-api:0.1.0`) and drive via CI/CD.
- [Low] No NetworkPolicies provided. Consider adding policies to restrict inter-namespace and inter-pod traffic, especially before production (Epic 5 scope).
- [Low] Ingress TLS commented; fine for local dev. Ensure cert-manager integration pre-production with proper TLS config.
- [Low] Secrets template is correct; ensure `.gitignore` excludes `k8s/secrets.yaml` (verified) and that CI never prints secret content.
- [Info] Health probes map correctly to FastAPI endpoints (src/api/health.py; k8s/deployment-api.yaml:65-91).

Tests and scripts:
- Unit manifest tests cover structure, resources, probes, and basic config (tests/unit/test_k8s_manifests.py).
- Integration tests scaffold cluster application and existence checks; slow tests are skipped without a cluster (tests/integration/test_k8s_deployment.py).
- Deployment validation script (`k8s/test-deployment.sh`) provides an end-to-end, operator-friendly validation flow.

