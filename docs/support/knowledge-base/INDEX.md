# Support Knowledge Base - Index

**AI Agents Platform Support Knowledge Base**

**Last Updated:** 2025-11-04
**Total Articles:** 10
**Categories:** FAQs (6), Known Issues (1), Troubleshooting (3)

---

## Quick Search by Symptom

| Symptom | Likely Cause | Article |
|---------|--------------|---------|
| "Enhancements not received" | Webhook delivery failure, queue backlog, worker crashes | [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) |
| "Enhancements taking too long" | High queue depth, slow external APIs, worker scaling issues | [FAQ: Slow Enhancements](faq-slow-enhancements.md) |
| "Enhancement quality poor" | Insufficient context, missing documentation, prompt tuning needed | [FAQ: Low Quality Enhancements](faq-low-quality-enhancements.md) |
| "Webhook setup not working" | Secret mismatch, URL typo, signature validation failure | [FAQ: Webhook Setup](faq-webhook-setup.md) |
| "Cannot access Grafana dashboards" | Login issues, datasource misconfiguration, permissions | [FAQ: Monitoring Dashboards](faq-monitoring-dashboards.md) |
| "High error rate in metrics" | Worker failures, external API timeouts, database issues | [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) |
| "RLS not enforcing correctly" | Session variable not set, policy misconfiguration | [Troubleshooting: RLS Issues](troubleshooting-rls-issues.md) |
| "Workers crashing frequently" | Memory limits exceeded (OOMKilled), application bugs | [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md) |

---

## Browse by Category

### Frequently Asked Questions (FAQs)

**Client-Reported Issues:**
1. [FAQ: Enhancements Not Received](faq-enhancements-not-received.md)
   - Webhook delivery failures
   - Queue backlog
   - Worker processing issues

2. [FAQ: Slow Enhancements](faq-slow-enhancements.md)
   - High queue depth
   - External API latency
   - Worker scaling delays

3. [FAQ: Low Quality Enhancements](faq-low-quality-enhancements.md)
   - Irrelevant suggestions
   - Missing context
   - Prompt tuning recommendations

**Setup & Configuration:**
4. [FAQ: Webhook Setup](faq-webhook-setup.md)
   - ServiceDesk Plus webhook configuration
   - Signature validation troubleshooting
   - Secret rotation procedures

5. [FAQ: Monitoring Dashboards](faq-monitoring-dashboards.md)
   - Grafana access and navigation
   - Prometheus query examples
   - Dashboard interpretation

6. [FAQ: Database Queries for Support](faq-database-queries.md)
   - RLS-compliant queries
   - Common investigation queries
   - Feedback API usage

---

### Known Issues

7. [Known Issues (November 2025)](known-issues.md)
   - Production deployment issues from Epic 5
   - Client-specific quirks
   - Planned fixes and workarounds

---

### Troubleshooting Guides

**Common Scenarios:**
8. [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md)
   - Worker failures
   - External API timeouts
   - Database connection issues

9. [Troubleshooting: RLS Issues](troubleshooting-rls-issues.md)
   - Cross-tenant access concerns
   - Session variable debugging
   - Policy verification

10. [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md)
    - OOMKilled diagnosis
    - Memory leak investigation
    - Worker restart procedures

---

## Browse by Component

### API Layer
- [FAQ: Webhook Setup](faq-webhook-setup.md)
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md)

### Worker Layer
- [FAQ: Slow Enhancements](faq-slow-enhancements.md)
- [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md)

### Database Layer
- [FAQ: Database Queries for Support](faq-database-queries.md)
- [Troubleshooting: RLS Issues](troubleshooting-rls-issues.md)

### Monitoring & Observability
- [FAQ: Monitoring Dashboards](faq-monitoring-dashboards.md)

### Client Experience
- [FAQ: Enhancements Not Received](faq-enhancements-not-received.md)
- [FAQ: Low Quality Enhancements](faq-low-quality-enhancements.md)

---

## Browse by Severity

### High Impact (P0/P1)
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) (if >10% error rate)
- [Troubleshooting: RLS Issues](troubleshooting-rls-issues.md) (security concern)
- [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) (if affecting all clients)

### Medium Impact (P2)
- [FAQ: Slow Enhancements](faq-slow-enhancements.md) (degraded service)
- [Troubleshooting: Worker Crashes](troubleshooting-worker-crashes.md) (if partial capacity)

### Low Impact (P3)
- [FAQ: Monitoring Dashboards](faq-monitoring-dashboards.md) (observability issues)
- [FAQ: Webhook Setup](faq-webhook-setup.md) (during onboarding)

---

## How to Use This Knowledge Base

### For Support Engineers

1. **Quick Search:** Use symptom table above to find relevant article
2. **Browse:** Navigate by category or component
3. **Bookmark:** Save frequently-used articles for rapid access
4. **Contribute:** Add new articles or update existing ones (see Maintenance section below)

### For New Team Members

**Recommended Reading Order:**
1. [FAQ: Monitoring Dashboards](faq-monitoring-dashboards.md) - Understand observability tools
2. [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) - Most common client issue
3. [FAQ: Webhook Setup](faq-webhook-setup.md) - Onboarding prerequisite
4. [Known Issues](known-issues.md) - Current known problems

### During Incidents

**Priority Access:**
- [Troubleshooting: High Error Rate](troubleshooting-high-error-rate.md) - High error rate incidents
- [Troubleshooting: RLS Issues](troubleshooting-rls-issues.md) - Security incidents
- [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) - Client-reported outages

---

## Knowledge Base Maintenance

### Update Process

**Who Can Update:**
- Support Engineers (L1, L2)
- Engineering Team (for technical corrections)
- Support Team Lead (approves significant changes)

**When to Update:**
1. **New Issue Discovered:** Create new article within 48 hours
2. **Known Issue Resolved:** Update known-issues.md immediately
3. **Process Changes:** Update affected articles within 1 week
4. **Feedback Received:** Review and update monthly

**How to Update:**
1. Edit markdown file directly in docs/support/knowledge-base/
2. Update "Last Updated" date at top of article
3. Add entry to version history at bottom
4. Post update in #support-docs-feedback Slack channel
5. (Optional) Get review from Support Team Lead for significant changes

---

### Article Template

**When creating new articles, use this structure:**

```markdown
# [Article Title]

**Category:** FAQ / Known Issue / Troubleshooting
**Severity:** P0 / P1 / P2 / P3
**Last Updated:** YYYY-MM-DD
**Related Runbooks:** [Link to runbooks if applicable]

---

## Quick Answer

[1-2 sentence summary for busy support engineers]

---

## Symptoms

- [List observable symptoms]
- [What client/user experiences]
- [What metrics/alerts show]

---

## Common Causes

1. [Cause 1 with explanation]
2. [Cause 2 with explanation]
3. [Cause 3 with explanation]

---

## Diagnosis Steps

**Step 1: [First diagnostic action]**
```bash
[Command or query]
```
Expected result: [What you should see]

**Step 2: [Second diagnostic action]**
[Instructions]

---

## Resolution

**If [Cause 1]:**
- [Resolution steps]

**If [Cause 2]:**
- [Resolution steps]

---

## Prevention

- [How to prevent recurrence]
- [Monitoring to add]
- [Process improvements]

---

## Escalation

**Escalate to L2/Engineering when:**
- [Condition 1]
- [Condition 2]

---

## Related Articles

- [Link to related KB articles]
- [Link to runbooks]
- [Link to documentation]

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | YYYY-MM-DD | Initial creation | [Name] |
```

---

## Feedback & Suggestions

**Report Issues:**
- Slack: #support-docs-feedback
- Email: support-lead@ai-agents.com
- Support ticket: Tag with "knowledge-base"

**Suggest New Articles:**
- Common issues you've encountered multiple times
- Client questions that aren't well-documented
- Process improvements discovered during troubleshooting

**Monthly Review:**
- Support Team Lead reviews all articles
- Updates statistics (total articles, categories)
- Archives outdated articles
- Promotes frequently-accessed articles to top

---

## Statistics

**Most Accessed Articles (Last 30 Days):**
1. FAQ: Enhancements Not Received (45 views)
2. FAQ: Slow Enhancements (32 views)
3. FAQ: Webhook Setup (28 views)
4. Troubleshooting: Worker Crashes (15 views)
5. FAQ: Monitoring Dashboards (12 views)

**Recently Added:**
- 2025-11-04: All initial articles created (Story 5.6)

**Last Updated Articles:**
- 2025-11-04: All articles (initial creation)

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial knowledge base index created (Story 5.6) | Dev Agent (AI) |

---

**Knowledge Base Ownership:** Support Team Lead
**Review Frequency:** Monthly
**Access:** All support team members, Engineering team (read-only)
