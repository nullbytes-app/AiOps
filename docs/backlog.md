# Engineering Backlog

This backlog collects cross-cutting or future action items that emerge from reviews and planning.

Routing guidance:

- Use this file for non-urgent optimizations, refactors, or follow-ups that span multiple stories/epics.
- Must-fix items to ship a story belong in that story’s `Tasks / Subtasks`.
- Same-epic improvements may also be captured under the epic Tech Spec `Post-Review Follow-ups` section.

| Date | Story | Epic | Type | Severity | Owner | Status | Notes |
| ---- | ----- | ---- | ---- | -------- | ----- | ------ | ----- |
| 2025-11-01 | 1.4 | 1 | Test | High | TBD | Closed | Added test + verified across restart. refs: tests/integration/test_redis_queue.py |
| 2025-11-01 | 1.4 | 1 | Enhancement | High | TBD | Closed | Helper added and endpoints refactored. refs: src/api/health.py |
| 2025-11-01 | 1.4 | 1 | Enhancement | Med | TBD | Closed | Added TimeoutError handling + structured logging. refs: src/services/queue_service.py |
| 2025-11-01 | 1.4 | 1 | Optimization | Low | TBD | Closed | Implemented per-loop shared client to avoid event loop issues. refs: src/cache/redis_client.py, src/services/queue_service.py |
| 2025-11-01 | 1.6 | 1 | Bug | High | TBD | Open | Run PostgreSQL as non-root in K8s (runAsUser: 999, runAsNonRoot: true). refs: k8s/deployment-postgres.yaml |
| 2025-11-01 | 1.6 | 1 | Enhancement | Med | TBD | Open | Align service manifests with file organization (split service YAMLs or update story tasks/file list). refs: k8s/deployment-*.yaml |
| 2025-11-01 | 1.6 | 1 | Enhancement | Low | TBD | Open | Pin API image tag, avoid `latest` in production. refs: k8s/deployment-api.yaml |
| 2025-11-01 | 1.6 | 1 | Enhancement | Med | TBD | Open | Pin Worker image tag (align with API), avoid `latest` in production. refs: k8s/deployment-worker.yaml |
