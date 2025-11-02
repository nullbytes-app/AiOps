# Senior Developer Review Report — Story 1.6 (Create Kubernetes Deployment Manifests)

Reviewer: Ravi
Date: 2025-11-01
Outcome: BLOCKED (critical security violation)

## Summary
Kubernetes manifests and documentation are largely complete and well structured with unit/integration tests and an automated validation script. However, a critical security violation exists in the PostgreSQL manifest (container configured to run as root). Additionally, services are embedded within deployment/statefulset manifests contrary to the story task/file list; functionally acceptable but diverges from the specified file organization.

## Key Findings

- [High] PostgreSQL container runs as root (`runAsNonRoot: false`) — violates architectural constraint that all containers must run as non-root. Remediation required before approval.
- [Med] Services defined inline rather than separate `k8s/service-*.yaml` files — recommend aligning implementation or updating story tasks/file list for traceability and consistency.
- [Low] API image tag uses `latest` — pin specific version for production readiness.
- [Low] No NetworkPolicies provided — advisable for production (Epic 5 scope).

## Acceptance Criteria Coverage
- 6/8 ACs implemented; AC7–AC8 require runtime validation in a cluster. See step-4.md for full checklist and evidence.

## Task Completion Validation
- Most tasks verified complete. Items calling for separate service YAMLs are implemented via embedded Service resources; marked QUESTIONABLE in checklist. See step-4.md for full details.

## Test Coverage and Gaps
- Unit tests validate manifest structure, resources, and probes.
- Integration tests exist; slow tests correctly skipped without a cluster.
- Validation script (`k8s/test-deployment.sh`) provides operator-focused flow.

## Architectural Alignment
- Generally aligned with architecture.md and tech-spec-epic-1.md regarding resources, probes, and structure.
- Violation: non-root execution for PostgreSQL.

## Security Notes
- Enforce non-root container execution where feasible; for PostgreSQL, set `runAsUser: 999`, `runAsNonRoot: true`, and consider `fsGroup: 999`.
- Keep TLS configuration commented for dev; enable cert-manager for production.

## Best-Practices and References
- docs/architecture.md — k8s directory structure and components
- docs/tech-spec-epic-1.md — resource requirements per service
- src/api/health.py — health/readiness endpoints for probes

## Action Items

### Code Changes Required
- [ ] [High] Configure PostgreSQL container to run as non-root (runAsNonRoot: true, runAsUser: 999; add fsGroup if needed) [file: k8s/deployment-postgres.yaml:72-75]
- [ ] [Med] Either split embedded Services into `k8s/service-*.yaml` files or update story tasks/file list to reflect combined manifests [files: k8s/deployment-*.yaml]
- [ ] [Low] Pin API image tag to a version and drive via CI/CD [file: k8s/deployment-api.yaml:31]

### Advisory Notes
- Note: Add NetworkPolicies before production to restrict traffic surfaces
- Note: Confirm validation on an actual cluster using `k8s/test-deployment.sh`
