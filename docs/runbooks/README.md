# Operational Runbooks - AI Agents Platform

**Last Updated:** 2025-11-03

This directory contains operational runbooks for diagnosing and resolving common production scenarios on the AI Agents Platform. Runbooks are organized by operational scenario and designed for rapid incident response.

---

## Quick Navigation

### Runbooks by Scenario

| Scenario | When to Use | Read Time |
|----------|------------|-----------|
| [High Queue Depth](./high-queue-depth.md) | Queue depth elevated (50-100 jobs) but not triggering alerts | 10 min |
| [Worker Failures](./worker-failures.md) | Worker crashes, restarts, or degradation | 12 min |
| [Database Connection Issues](./database-connection-issues.md) | PostgreSQL connectivity problems or slow queries | 15 min |
| [API Timeout](./api-timeout.md) | External API failures (ServiceDesk Plus, OpenAI) | 12 min |
| [Tenant Onboarding](./tenant-onboarding.md) | Adding new MSP client to platform | 20 min |

### Search Keywords for Rapid Navigation

**By Symptom:**
- Queue backing up → [High Queue Depth](./high-queue-depth.md)
- Worker restarting → [Worker Failures](./worker-failures.md)
- Database errors → [Database Connection Issues](./database-connection-issues.md)
- Timeouts in logs → [API Timeout](./api-timeout.md)
- New customer setup → [Tenant Onboarding](./tenant-onboarding.md)

**By Component:**
- Redis queue → [High Queue Depth](./high-queue-depth.md)
- Celery workers → [Worker Failures](./worker-failures.md), [High Queue Depth](./high-queue-depth.md)
- PostgreSQL → [Database Connection Issues](./database-connection-issues.md)
- External APIs → [API Timeout](./api-timeout.md)
- Tenant configuration → [Tenant Onboarding](./tenant-onboarding.md)

---

## Runbook Structure

All operational runbooks follow a standardized format for consistency and ease of use during incident response:

### Standard Sections

1. **Overview:** Scope of runbook, when to use, common triggers
2. **Quick Links:** Jump navigation to key sections
3. **Symptoms:** Observable indicators that this runbook applies
4. **Diagnosis:** Step-by-step investigation commands and expected outputs
5. **Resolution:** Ordered remediation procedures
6. **Escalation:** When/how to escalate, SLA thresholds
7. **Using Distributed Tracing:** Jaeger UI guidance for end-to-end diagnostics
8. **Related Documentation:** Links to other runbooks, setup guides, and reference material

### Command Format

All diagnostic and remediation commands in runbooks are **copy-paste ready**:
- No placeholder values (use actual values or clear variable references)
- Both Docker and Kubernetes variants provided where applicable
- Expected output examples shown for commands that may be unfamiliar

### Runbook vs Alert Runbook

| Aspect | Alert Runbook | Operational Runbook |
|--------|--------------|-------------------|
| Triggered by | Prometheus alert firing | Proactive investigation or non-alert scenario |
| Location | `docs/operations/alert-runbooks.md` | `docs/runbooks/*.md` |
| Examples | EnhancementSuccessRateLow, QueueDepthHigh | High Queue Depth (pre-alert), Worker Failures (post-mortem) |
| When to use | Alert fired in Prometheus | Metric elevated but below alert threshold OR incident post-mortem |

---

## Maintenance and Review Process

### Quarterly Runbook Review Schedule

**Every 3 months (plus after major incidents):**

1. **Verify commands still execute successfully**
   - Test all kubectl/docker-compose commands in both local and production environments
   - Verify Prometheus queries still return valid results
   - Check external links (Grafana, Jaeger, Prometheus URLs)

2. **Update screenshots and expected outputs**
   - UI screenshots become outdated with Grafana/Jaeger updates
   - Command output examples may change with dependency versions
   - Note Kubernetes version changes that affect kubectl behavior

3. **Check for new failure modes**
   - Review incident postmortems from last quarter
   - Identify any scenarios not covered by existing runbooks
   - Add new runbooks or extend existing ones as needed

4. **Review git history for code changes**
   - Check if recent application code changes affect runbook procedures
   - Example: Database migration affecting RLS policies → update database-connection-issues.md
   - Example: New worker configuration option → update worker-failures.md

5. **Test with new team member (spot check)**
   - Have a newer team member follow 1-2 runbooks without assistance
   - Document any confusion or ambiguous instructions
   - Apply improvements immediately

6. **Validate external integrations**
   - Verify ServiceDesk Plus API endpoints still exist (tenant-onboarding.md)
   - Check OpenAI API status page URL (api-timeout.md)
   - Confirm Jaeger retention policies haven't changed (tracing examples)

### Version Control and Tagging

**Commit messages for runbook updates:**

```
Runbook update: [scenario] - [summary of changes]

Example: "Runbook update: worker-failures - Add memory profiling procedure after OOMKilled incidents"
```

**Tag major revisions:**

```bash
git tag runbooks-v1.1
git tag runbooks-v1.2-database-failover  # Include context if significant addition
```

**Update metadata in each runbook:**
- Update "Last Updated" date at top of file
- Update author if different from original
- Add brief note of changes in Comments section if substantial

### Post-Incident Runbook Updates

**After major incident is resolved:**

1. On-call engineer (or incident commander) updates relevant runbook
2. Add new "Common Issues" subsection if novel failure mode discovered
3. Update "Resolution" section if new remediation procedure identified
4. Git commit message references incident ticket/postmortem:
   ```
   Runbook update: database-connection-issues - Add new RLS troubleshooting steps

   Ref: INC-2025-11-15 - Row level security bug caused ticket access denied
   See: https://incident-tracker.com/incidents/INC-2025-11-15
   ```

### Responsibility Assignment

| Role | Responsibility |
|------|-----------------|
| **Operations Team** | Owns quarterly review process scheduling and execution |
| **On-call Engineer** | Responsible for post-incident runbook updates |
| **Engineering Team** | Reviews technical accuracy during quarterly check, suggests improvements |
| **Product Manager** | Notified of new runbooks that change operational procedures |

---

## Using Runbooks During Incidents

### Step-by-Step Incident Response Process

1. **Identify the problem**
   - What symptoms are you observing? (metric spike, errors in logs, user complaints)
   - Use the "Search Keywords" table above to find relevant runbook

2. **Read the Overview section**
   - Confirm this runbook applies to your situation
   - Review prerequisites and scope
   - Note any warnings or special considerations

3. **Review Symptoms section**
   - Match observed symptoms to runbook description
   - If symptoms don't match closely, try different runbook
   - Document which symptoms you're seeing for escalation if needed

4. **Execute Diagnosis section**
   - Follow commands **in order**
   - Copy-paste commands as-is (they're already correct)
   - Compare your output to "Expected Output" examples
   - Collect findings (screenshot, save output to file if needed)

5. **Execute Resolution section**
   - Again, follow **in order**
   - Validate after each major step (test connectivity, verify metric, etc.)
   - If issue not resolved after Resolution steps, check Escalation section

6. **Use Distributed Tracing for deep diagnostics**
   - If diagnosis doesn't identify root cause, open Jaeger UI
   - Use Jaeger queries provided in "Using Distributed Tracing" section
   - Review trace timeline to identify bottleneck or failure point

7. **Escalate if needed**
   - Follow Escalation section for when/how to page on-call
   - Reference which runbook steps you've completed
   - Have diagnostic output ready for escalated team

### Tips for Effective Runbook Use Under Pressure

- **Read full runbook first (2 min):** Don't jump to commands; understand full procedure
- **Create incident notes:** Paste runbook sections into incident ticket as you work through them
- **Save command output:** Grep/redirect output to file for later analysis and postmortem
- **Ask questions:** If runbook is unclear, ask in Slack #ops-incidents channel (don't guess)
- **Time yourself:** Track how long each step takes; this data helps with SLA planning
- **Provide feedback:** After incident, file improvement issues for unclear runbook sections

---

## Related Documentation

### Operational Setup Guides

- **[Prometheus Setup](../operations/prometheus-setup.md)** - Metrics collection infrastructure
- **[Grafana Setup](../operations/grafana-setup.md)** - Monitoring dashboards and visualization
- **[Alert Rules Configuration](../operations/prometheus-alerting.md)** - Alert threshold definitions
- **[Alertmanager Setup](../operations/alertmanager-setup.md)** - Alert routing and notifications
- **[Distributed Tracing Setup](../operations/distributed-tracing-setup.md)** - OpenTelemetry and Jaeger configuration

### Alert Runbooks

- **[Alert Runbooks](../operations/alert-runbooks.md)** - Procedures for 4 automated alerts (EnhancementSuccessRateLow, QueueDepthHigh, WorkerDown, HighLatency)

### Central Operational Index

- **[Operations Documentation Index](../operations/README.md)** - Central hub for all operational procedures and guides

### Developer Documentation

- **[Architecture Documentation](../architecture.md)** - System design and component interactions
- **[API Documentation](../api.md)** - REST API endpoints and integrations
- **[Database Schema](../database-schema.md)** - PostgreSQL tables, relationships, RLS policies

---

## Review Template

Use this template when conducting quarterly runbook reviews:

**File:** `docs/runbooks/review-template.md`

```markdown
# Runbook Review - [Date]

## Reviewed Runbooks

- [ ] high-queue-depth.md
- [ ] worker-failures.md
- [ ] database-connection-issues.md
- [ ] api-timeout.md
- [ ] tenant-onboarding.md

## Review Checklist

### For Each Runbook

- [ ] Commands tested and working (Docker and Kubernetes)
- [ ] Prometheus queries return valid results
- [ ] External links verified (Grafana, Jaeger, API status pages)
- [ ] Screenshots/example outputs current
- [ ] No references to deprecated components or APIs
- [ ] Jaeger query examples still valid

### Overall

- [ ] No new failure modes from incidents this quarter
- [ ] New application features require runbook updates
- [ ] Dependencies updated (K8s, database versions)
- [ ] Team feedback collected and addressed

## Findings and Action Items

[Document findings, improvements needed, new runbooks to create]

## Approved By

- Operations Lead: _______________
- Engineering Lead: _______________

## Next Review Date

[Date 3 months from review]
```

---

## Quick Reference: Running Commands by Environment

### Docker (Local Development)

```bash
# View worker logs
docker-compose logs -f worker

# Restart worker
docker-compose restart worker

# Connect to Redis
docker-compose exec redis redis-cli

# Connect to PostgreSQL
docker-compose exec postgres psql -U aiagents -d ai_agents

# Check queue depth
docker-compose exec redis redis-cli LLEN enhancement_queue
```

### Kubernetes (Production)

```bash
# View worker logs
kubectl logs -f -l app=celery-worker --tail=100

# Restart workers
kubectl rollout restart deployment/celery-worker

# Connect to Redis pod
kubectl exec -it redis-0 -- redis-cli

# Connect to PostgreSQL
kubectl exec -it postgres-0 -- psql -U aiagents -d ai_agents

# Check queue depth
kubectl exec -it redis-0 -- redis-cli LLEN enhancement_queue
```

---

## Runbook Validation Report

See `docs/operations/runbook-validation-report.md` for:
- Team member testing results
- Time to complete each runbook
- Ambiguities identified and resolved
- Improvements applied based on feedback

---

**For operational emergencies, start with appropriate runbook above. For product questions, contact Product team. For code changes, see developer documentation.**
