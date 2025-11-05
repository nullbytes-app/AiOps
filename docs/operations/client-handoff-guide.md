# Client Handoff Guide for Support Team

**Version:** 1.0
**Last Updated:** 2025-11-03
**Owner:** Customer Success & Support Team
**Status:** Production Ready

---

## Table of Contents

1. [Overview](#overview)
2. [Support Team Responsibilities](#support-team-responsibilities)
3. [Client Information](#client-information)
4. [Day-to-Day Operations](#day-to-day-operations)
5. [Client Communication](#client-communication)
6. [Escalation Procedures](#escalation-procedures)
7. [Monitoring & Alerts](#monitoring--alerts)
8. [References](#references)

---

## Overview

### Purpose

This guide defines support team responsibilities for newly onboarded MSP clients on the AI Agents Ticket Enhancement Platform. It covers day-to-day operations, monitoring, escalation procedures, and client communication protocols.

### Scope

- Post-onboarding client support (after production activation)
- Issue investigation and triage
- Performance monitoring
- Client satisfaction tracking
- Enhancement quality feedback loop

### Support Model

- **Tier 1 Support:** Client-facing, initial triage, common issues
- **Tier 2 Support:** Deep technical investigation, escalation to engineering
- **Engineering:** Code fixes, infrastructure changes, security incidents

---

## Support Team Responsibilities

### Daily Responsibilities

**1. Monitor Client Health Dashboards**

```bash
# Check Grafana dashboard for all active tenants (first thing each morning)
# URL: http://grafana.production.local/d/tenant-health-overview
```

**Key metrics to review:**
- Enhancement success rate (target: > 95%)
- Average latency (target: < 15 seconds)
- Failed requests in last 24 hours (target: < 10)
- Queue depth (target: < 50)

**2. Review Support Tickets**

- Check support inbox for new client inquiries
- Triage by severity (P0/P1/P2/P3)
- Respond to P2/P3 within SLA (2 hours / 24 hours)
- Escalate P0/P1 immediately

**3. Client Check-ins (New Clients)**

- **Week 1:** Daily check-in (proactive outreach)
- **Week 2-4:** 3x/week check-in
- **Month 2+:** Weekly or as-needed

### Weekly Responsibilities

**1. Client Satisfaction Survey**

Send weekly survey to client admins:

```
Subject: How's AI Ticket Enhancement performing?

Hi [Client Name],

Quick check-in on your experience with AI ticket enhancements this week:

1. Enhancement relevance: [1-5 stars]
2. Enhancement helpfulness: [1-5 stars]
3. Any issues or concerns? [Free text]

Your feedback helps us improve!

Best,
[Support Team]
```

**2. Review Enhancement Quality**

Sample 10 random enhancements per client per week:
- Read enhancement text
- Evaluate relevance to ticket
- Check for hallucinations or nonsensical output
- Flag quality issues to engineering

**3. Update Client Profile**

Document any configuration changes, feedback themes, or notable incidents in:
- `docs/clients/<client-name>/weekly-notes/YYYY-MM-DD.md`

### Monthly Responsibilities

**1. Monthly Business Review (MBR)**

Schedule 30-minute call with client admin:

**Agenda:**
- Review month's metrics (volume, success rate, latency)
- Discuss client feedback trends
- Identify improvement opportunities
- Preview upcoming features
- Discuss expansion (additional technicians, premium tier)

**2. Generate Monthly Report**

Send automated metrics report:
- Total tickets enhanced
- Average enhancement latency
- Success rate
- Top 5 issue categories addressed
- Cost savings estimate (time saved for technicians)

---

## Client Information

### Where to Find Client Details

**Database:**
```sql
-- Query tenant configuration
SELECT tenant_id, name, servicedesk_url, created_at,
       enhancement_preferences, rate_limits
FROM tenant_configs
WHERE tenant_id = '<TENANT_ID>';
```

**File System:**
```
docs/clients/<client-name>/
├── profile.md              # Company info, contacts, support tier
├── config.md               # Technical configuration details
├── baseline-metrics.md     # Initial performance metrics
├── weekly-notes/           # Support team notes
│   └── YYYY-MM-DD.md
└── feedback/               # Client feedback records
    └── YYYY-MM-DD-survey.md
```

**Client Profile Template (`profile.md`):**

```markdown
# Client Profile: [Company Name]

**Tenant ID:** 550e8400-e29b-41d4-a716-446655440000
**Company Name:** Acme Corp MSP
**Support Tier:** Basic / Premium
**Onboarding Date:** 2025-11-03
**Onboarding Engineer:** Alice Johnson

## Contacts

**Admin Contact:**
- Name: John Smith
- Email: john.smith@acmecorp.com
- Phone: +1-555-1234
- Role: IT Director

**Secondary Contact:**
- Name: Jane Doe
- Email: jane.doe@acmecorp.com
- Phone: +1-555-5678
- Role: ServiceDesk Manager

**Escalation Contact:**
- Name: Bob Wilson (CEO)
- Email: bob.wilson@acmecorp.com
- Phone: +1-555-9999

## ServiceDesk Plus Details

**URL:** https://servicedesk.acmecorp.com
**API Version:** v3
**Webhook Configured:** Yes (2025-11-03)
**Webhook URL:** https://api.ai-agents.production/webhook/servicedesk?tenant_id=550e8400...

## Support Tier Details

**Tier:** Basic
- **Namespace:** Shared production namespace
- **Rate Limits:** 100 requests/min
- **SLA:** 24-hour response (P2), 2-hour response (P1)
- **Support Hours:** Business hours (9am-5pm ET, Mon-Fri)

## Notes

- Client uses ServiceDesk Plus Cloud (not on-premise)
- Primary use case: Network infrastructure tickets
- ~500 tickets/month volume
- Onboarding feedback: "Very impressed with enhancement quality" (5/5 stars)
```

---

## Day-to-Day Operations

### Handling Client Inquiries

#### Common Question 1: "Why didn't my ticket get an enhancement?"

**Investigation Steps:**

1. **Get ticket ID from client:**
   - "Can you provide the ServiceDesk Plus ticket ID? (e.g., TKT-12345)"

2. **Query enhancement history:**
```sql
SELECT ticket_id, status, error_message, created_at, completed_at
FROM enhancement_history
WHERE tenant_id = '<TENANT_ID>'
  AND ticket_id = 'TKT-12345';
```

3. **Possible scenarios:**

**Scenario A: No record found**
```
Investigation: Webhook not delivered
- Check FastAPI logs: kubectl logs -n production deployment/ai-agents-api | grep "TKT-12345"
- If no logs: Webhook not sent from ServiceDesk Plus
- Ask client to verify webhook configuration still active
- Test webhook from ServiceDesk Plus admin
```

**Scenario B: Status = 'failed'**
```
Investigation: Processing error occurred
- Check error_message column for details
- Common errors:
  * "Signature validation failed" → See Troubleshooting Guide, Issue 1B
  * "ServiceDesk Plus API 401" → Credentials expired, update tenant_configs
  * "LLM API rate limit" → Temporary, should retry automatically
- If unclear: Escalate to Tier 2
```

**Scenario C: Status = 'completed'**
```
Investigation: Enhancement was posted
- Ask client: "Have you checked the ticket notes/comments section?"
- ServiceDesk Plus may hide notes under "Show Internal Notes" toggle
- Verify enhancement visible in ServiceDesk Plus ticket view
- If client can't see: ServiceDesk Plus permissions issue (their IT)
```

#### Common Question 2: "The enhancement isn't relevant to my ticket"

**Investigation Steps:**

1. **Review enhancement content:**
```sql
SELECT enhancement_text, confidence_score, context_used
FROM enhancement_history
WHERE tenant_id = '<TENANT_ID>'
  AND ticket_id = 'TKT-12345';
```

2. **Evaluate enhancement quality:**
   - Does it address the ticket subject/description?
   - Are suggestions actionable?
   - Any hallucinations or incorrect information?

3. **Check ticket history volume:**
```sql
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = '<TENANT_ID>';
-- If < 50: Insufficient data for quality enhancements
```

4. **Response to client:**

**If insufficient data:**
```
"Thanks for the feedback! We're still building context from your ticket history.
Enhancement quality typically improves after we have 100+ resolved tickets in our database.

Would you like us to import your historical tickets (last 90 days) to improve relevance?"
```

**If enhancement genuinely poor:**
```
"Thanks for flagging this. I've reviewed the enhancement and agree it's not relevant.
I've logged this as a quality issue for our engineering team to investigate.

We're constantly improving our AI models. Would you be open to a brief call this week
to discuss what type of suggestions would be most helpful for your team?"
```

5. **Document feedback:**
   - Create file: `docs/clients/<client-name>/feedback/YYYY-MM-DD-ticket-TKT-12345.md`
   - Include: Ticket summary, enhancement text, client feedback, action items
   - Tag engineering team in Slack `#ai-quality-feedback`

#### Common Question 3: "How do I adjust enhancement settings?"

**Configuration Options:**

**1. LLM Model Selection:**
```sql
-- Upgrade to more capable model (costs more)
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{llm_model}',
    '"openai/gpt-4o"'  -- Default: gpt-4o-mini
)
WHERE tenant_id = '<TENANT_ID>';
```

**2. Enhancement Length:**
```sql
-- Increase max tokens for longer enhancements
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{max_tokens}',
    '750'  -- Default: 500
)
WHERE tenant_id = '<TENANT_ID>';
```

**3. Context Sources:**
```sql
-- Add/remove context sources
UPDATE tenant_configs
SET enhancement_preferences = jsonb_set(
    enhancement_preferences,
    '{context_sources}',
    '["ticket_history", "kb", "monitoring", "system_inventory"]'::jsonb
)
WHERE tenant_id = '<TENANT_ID>';
```

**Response to client:**
```
"We can definitely adjust your enhancement settings! Here are the options:

1. **Enhancement length:** Shorter (300 tokens) vs Longer (750 tokens)
2. **Detail level:** Quick suggestions vs Detailed analysis
3. **Model:** Standard (fast, cost-effective) vs Advanced (more capable, higher cost)

Would you like to schedule a 15-minute call to discuss your preferences?"
```

---

## Client Communication

### Communication Channels

**Primary:**
- **Email:** support@ai-agents.company.com
- **Response SLA:** P2 (2 hours), P3 (24 hours)

**Secondary:**
- **Slack Connect:** (for Premium tier clients)
- **Phone:** (for P0/P1 emergencies only)

### Email Templates

#### Template 1: Onboarding Complete

```
Subject: Welcome to AI Agents Ticket Enhancement Platform!

Hi [Client Admin Name],

Congratulations! Your team is now live on the AI Agents platform.

**What to expect:**
- Tickets submitted to ServiceDesk Plus will automatically receive AI-generated enhancements
- Enhancements appear in ticket notes/comments within 10-15 seconds
- Our AI learns from your ticket history to provide more relevant suggestions over time

**Next steps:**
1. Create a test ticket to see the enhancement in action
2. Share feedback with our team (good or bad - we want to hear it!)
3. Schedule your Week 1 check-in call: [Calendly link]

**Support:**
- Email: support@ai-agents.company.com
- Documentation: [link to client portal]
- Your dedicated support engineer: [Name]

Looking forward to helping your team resolve tickets faster!

Best,
[Support Team]
```

#### Template 2: Weekly Check-in (Week 1)

```
Subject: Week 1 Check-in: How's AI Enhancement Working?

Hi [Client Admin Name],

Quick check-in after your first week with AI ticket enhancements!

**Your metrics so far:**
- Tickets enhanced: 47
- Success rate: 98%
- Average latency: 12 seconds

**Questions for you:**
1. Are enhancements showing up as expected in ServiceDesk Plus?
2. How are your technicians responding to the AI suggestions?
3. Any issues or concerns we should address?

**This week's highlights:**
- [Example of particularly good enhancement for client]
- [Any quality issues identified and addressed]

Let's schedule a 15-minute call to discuss: [Calendly link]

Best,
[Support Team]
```

#### Template 3: Monthly Business Review Invitation

```
Subject: [Company Name] Monthly Review - [Month YYYY]

Hi [Client Admin Name],

Time for our monthly review! Let's discuss your AI enhancement metrics and any feedback.

**Proposed times:**
- [Option 1: Date/Time]
- [Option 2: Date/Time]
- [Option 3: Date/Time]

**Agenda (30 minutes):**
1. Review metrics (volume, success rate, latency)
2. Quality feedback discussion
3. New features preview
4. Expansion opportunities

**Pre-read:** [Link to monthly metrics report]

Looking forward to connecting!

Best,
[Support Team]
```

---

## Escalation Procedures

### When to Escalate to Tier 2 / Engineering

| Situation | Escalate To | Timeline |
|-----------|-------------|----------|
| Multiple clients reporting same issue | Engineering Lead | Immediate |
| Client reports data leak / sees other client's data | Security Team + Engineering Director | IMMEDIATE (P0) |
| Enhancement failure rate > 10% for 2+ hours | On-call Engineer | 30 minutes |
| RLS validation fails | Engineering Director | IMMEDIATE (P0) |
| LLM API down / rate limited | Engineering Lead | 1 hour |
| Client escalation (C-level complaint) | Customer Success Manager + VP Engineering | 2 hours |
| Request for custom integration | Engineering Lead + Product Manager | Next business day |

### Escalation Process

**1. Gather information:**
   - Tenant ID
   - Issue description and symptoms
   - Timeline (when did issue start?)
   - Impact (how many clients affected?)
   - Client severity (Basic vs Premium tier)
   - Any error messages or logs

**2. Create incident ticket:**
   - Title format: `[TENANT-NAME] Issue description`
   - Priority: P0/P1/P2/P3
   - Assigned to: Engineering Lead or On-call Engineer
   - Tags: `tenant-issue`, `client-impact`, relevant client name

**3. Notify stakeholders:**
   - **P0/P1:** Page on-call engineer via PagerDuty
   - **P0/P1:** Post in `#incidents` Slack channel
   - **P2:** Email engineering lead
   - **P3:** Add to engineering backlog

**4. Keep client informed:**
   - Acknowledge issue within 1 hour (P0/P1) or 2 hours (P2)
   - Provide status updates every 2 hours (P0/P1) or daily (P2/P3)
   - Share resolution ETA if known
   - Conduct post-mortem with client (P0/P1 only)

---

## Monitoring & Alerts

### Grafana Dashboards

**Access Grafana:**
```bash
# Production Grafana
URL: https://grafana.ai-agents.production
Login: [Your SSO credentials]
```

**Key Dashboards:**

1. **Tenant Health Overview** (`/d/tenant-health-overview`)
   - All active tenants in single view
   - Success rate, latency, request volume
   - Sortable by metric (identify struggling clients)

2. **Per-Tenant Deep Dive** (`/d/tenant-metrics?var-tenant_id=<UUID>`)
   - Single tenant focus
   - Enhancement pipeline stages (webhook → queue → worker → completion)
   - Error breakdown by type
   - Latency percentiles (p50, p95, p99)

3. **System-Wide Health** (`/d/system-overview`)
   - Infrastructure status (API pods, workers, database, Redis)
   - Queue depth over time
   - Worker utilization
   - Database connection pool usage

### Alert Handling

**Alertmanager sends alerts to:**
- Slack channel: `#alerts-production`
- PagerDuty: (P0/P1 only)
- Email: support team distribution list

**Common Alerts:**

**Alert 1: EnhancementFailureRateHigh**
```
Description: Enhancement failure rate > 5% for 10 minutes
Severity: P2 (or P1 if > 50%)
Action:
1. Check Grafana for affected tenants
2. Review error logs for common error patterns
3. If single tenant: Investigate tenant-specific issue (credentials, ServiceDesk Plus API)
4. If multiple tenants: System-wide issue, escalate to engineering
```

**Alert 2: HighLatency**
```
Description: p95 latency > 30 seconds for 5 minutes
Severity: P2
Action:
1. Check Jaeger for slow spans (which component bottleneck?)
2. Review worker resource utilization (CPU/memory)
3. Check LLM API status (OpenRouter status page)
4. Check ServiceDesk Plus API responsiveness (ask client if their system slow)
5. Consider scaling workers: kubectl scale deployment ai-agents-worker --replicas=5
```

**Alert 3: QueueDepthHigh**
```
Description: Redis queue depth > 100 for 10 minutes
Severity: P2
Action:
1. Check worker pod status (all running?)
2. Check worker logs for stuck tasks
3. Scale workers horizontally: kubectl scale deployment ai-agents-worker --replicas=5
4. If queue not decreasing, restart workers: kubectl rollout restart deployment/ai-agents-worker
```

**Alert 4: RLSViolation (CRITICAL)**
```
Description: RLS policy check failed / cross-tenant data detected
Severity: P0
Action:
1. IMMEDIATELY disable all workers: kubectl scale deployment ai-agents-worker --replicas=0
2. Page security team + engineering director
3. Run RLS validation script: ./scripts/tenant-isolation-validation.sh
4. DO NOT re-enable workers until RLS validated by engineering
5. Notify affected clients within 72 hours (GDPR compliance)
```

---

## References

### Internal Documentation

- **[Client Onboarding Runbook](client-onboarding-runbook.md)** - Onboarding procedures (for understanding client setup)
- **[Tenant Troubleshooting Guide](tenant-troubleshooting-guide.md)** - Detailed troubleshooting steps
- **[Production Deployment Runbook](production-deployment-runbook.md)** - Infrastructure operations
- **[Architecture Documentation](../architecture.md)** - System design overview

### Support Tools

- **Grafana:** https://grafana.ai-agents.production
- **Jaeger:** https://jaeger.ai-agents.production
- **PagerDuty:** https://company.pagerduty.com
- **Slack Channels:**
  - `#support-team` - Support team coordination
  - `#alerts-production` - Automated alerts
  - `#incidents` - Active incidents
  - `#ai-quality-feedback` - Enhancement quality issues

### Client Portal

- **Documentation:** https://docs.ai-agents.company.com
- **Status Page:** https://status.ai-agents.company.com
- **Support Tickets:** https://support.ai-agents.company.com

### External References

- [ServiceDesk Plus API Documentation](https://www.manageengine.com/products/service-desk/sdpod-v3-api/)
- [PostgreSQL RLS Documentation](https://www.postgresql.org/docs/17/ddl-rowsecurity.html)

---

## Appendix: Useful SQL Queries

### Get Tenant Overview
```sql
SELECT t.tenant_id,
       t.name,
       COUNT(DISTINCT eh.ticket_id) as tickets_enhanced_lifetime,
       AVG(eh.duration_seconds) as avg_duration,
       SUM(CASE WHEN eh.status = 'completed' THEN 1 ELSE 0 END)::float /
         NULLIF(COUNT(*), 0) * 100 as success_rate_pct
FROM tenant_configs t
LEFT JOIN enhancement_history eh ON t.tenant_id = eh.tenant_id
WHERE t.tenant_id = '<TENANT_ID>'
GROUP BY t.tenant_id, t.name;
```

### Recent Enhancement Activity (Last 7 Days)
```sql
SELECT DATE(created_at) as date,
       COUNT(*) as requests,
       SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed,
       SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
       AVG(duration_seconds) as avg_duration
FROM enhancement_history
WHERE tenant_id = '<TENANT_ID>'
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

### Failed Enhancements (Last 24 Hours)
```sql
SELECT ticket_id,
       error_message,
       created_at
FROM enhancement_history
WHERE tenant_id = '<TENANT_ID>'
  AND status = 'failed'
  AND created_at > NOW() - INTERVAL '24 hours'
ORDER BY created_at DESC;
```

---

**Document Version History:**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2025-11-03 | Customer Success Team | Initial release (Story 5.3) |

**Review Schedule:** Quarterly review, next due 2026-02-03
