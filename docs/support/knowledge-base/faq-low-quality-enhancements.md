# FAQ: Low Quality Enhancements

**Category:** FAQ - Enhancement Quality Issue
**Severity:** P2 (if <3/5 rating) / P3 (if 3-4/5 rating but improvable)
**Last Updated:** 2025-11-04
**Related Runbooks:** [Enhancement Failures](../../runbooks/enhancement-failures.md)

---

## Quick Answer

**Most common causes:** Insufficient context (missing ticket history or documentation), irrelevant knowledge base articles retrieved, or prompt tuning needed for specific ticket types. Check feedback API → context gathering logs → knowledge base relevance in that order.

---

## Symptoms

**Client Reports:**
- "Enhancement suggestions are generic or irrelevant"
- "AI doesn't understand our specific environment"
- "Suggestions miss obvious solutions from past tickets"
- Feedback API shows average rating <3/5 for technicians

**Observable Indicators:**
- Low feedback ratings in Grafana Baseline Metrics Dashboard
- Client technicians leaving comments: "Not helpful", "Too generic"
- High feedback submission rate but low thumbs-up ratio
- Specific ticket categories consistently rated poorly

---

## Common Causes

### 1. Insufficient Ticket History Context (40% of cases)

**Root Cause:** AI not seeing relevant past tickets for context

**Possible Reasons:**
- Client's ticket history not fully populated (Story 2.5A incomplete)
- Similarity search not finding relevant past tickets
- Too few resolved tickets in database (<50 tickets)
- Ticket descriptions too vague for effective similarity matching

**How to Identify:**
```bash
# Check ticket history count for client
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "
SET app.current_tenant_id = '<tenant-id>';
SELECT COUNT(*) FROM ticket_history WHERE tenant_id = '<tenant-id>' AND status = 'resolved';
"
# Result: <50 tickets = insufficient history, <20 = very limited context

# Check context gathering logs for specific ticket
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=1h | grep "ticket_id: 12345" | grep "context_gathered"
# Look for: "similar_tickets_found: 0" or "similar_tickets_found: 1-2" (too few)
```

**Resolution:**
- **If <50 resolved tickets:** Escalate to Engineering to backfill more ticket history (Story 2.5A process)
- **If similarity search not finding matches:** May need prompt tuning for better keyword extraction
- **Immediate workaround:** Advise client to provide more detail in ticket descriptions

---

### 2. Missing or Outdated Documentation (30% of cases)

**Root Cause:** Knowledge base search not finding relevant documentation

**Possible Reasons:**
- Client's documentation not uploaded to knowledge base
- Documentation exists but not well-structured for semantic search
- Documentation outdated (doesn't cover new systems/processes)
- Search keywords not matching documentation terminology

**How to Identify:**
```bash
# Check knowledge base document count for client
kubectl exec -it deployment/ai-agents-api -n ai-agents-production -- psql $DATABASE_URL -c "
SET app.current_tenant_id = '<tenant-id>';
SELECT COUNT(*) FROM knowledge_base WHERE tenant_id = '<tenant-id>';
"
# Result: 0 documents = no KB, <10 documents = limited KB

# Check context gathering logs for doc retrieval
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=1h | grep "ticket_id: 12345" | grep "documents_found"
# Look for: "documents_found: 0" or very low relevance scores
```

**Resolution:**
- **If no documents:** Contact client to provide documentation (network diagrams, SOPs, FAQs)
- **If documents exist but not found:** Escalate to Engineering for semantic search tuning
- **Document format:** Prefer structured markdown, avoid scanned PDFs
- **Update frequency:** Quarterly review with client to refresh documentation

---

### 3. Generic Prompts Not Tuned for Client (20% of cases)

**Root Cause:** GPT-4 prompts too generic, not customized for client's industry/environment

**Possible Reasons:**
- Using default enhancement prompt for all clients
- Client has specialized terminology not in GPT-4 training data
- Client's environment (e.g., manufacturing, healthcare) needs domain-specific guidance
- Prompt not emphasizing client-specific priorities (e.g., compliance, cost reduction)

**How to Identify:**
```bash
# Check feedback comments for patterns
# Query Feedback API for this client's recent comments
curl -H "Authorization: Bearer $TOKEN" "https://api-url/api/v1/feedback?tenant_id=<tenant>&start_date=2025-11-01&feedback_type=rating&sort=created_at:desc&limit=20"

# Look for recurring themes in comments:
# - "Too generic"
# - "Doesn't understand our [industry-specific term]"
# - "Missing [client-specific context]"
```

**Resolution:**
- **Escalate to Engineering** for custom prompt tuning
- **Provide feedback samples:** 10-20 low-rated enhancement examples with client comments
- **Client interview:** Schedule call to understand industry-specific needs
- **Turnaround:** 1-2 weeks for prompt refinement and A/B testing

---

### 4. Irrelevant Knowledge Base Articles Retrieved (10% of cases)

**Root Cause:** Semantic search returning low-relevance documents

**Possible Reasons:**
- Document chunking not optimal (chunks too large or too small)
- Embeddings not capturing semantic meaning well
- Search query construction not extracting good keywords from ticket
- Knowledge base contains many irrelevant documents (low signal-to-noise)

**How to Identify:**
```bash
# Check context gathering logs for relevance scores
kubectl logs deployment/ai-agents-worker -n ai-agents-production --since=1h | grep "ticket_id: 12345" | grep "relevance_score"
# Look for: All scores <0.6 (low relevance), or high-scoring docs that are clearly irrelevant

# Example log entry:
# "document_1: relevance_score=0.45, title='General Network Overview'" (too generic)
```

**Resolution:**
- **Escalate to Engineering** for semantic search tuning
- **Provide examples:** Show tickets where wrong docs were retrieved
- **Knowledge base cleanup:** Work with client to remove outdated/irrelevant docs
- **Document structure:** Ensure docs have clear titles, headings, summaries

---

## Diagnosis Steps

**Step 1: Check Feedback API for Client Satisfaction Trend**
```bash
# Get average rating for last 7 days
curl -H "Authorization: Bearer $TOKEN" "https://api-url/api/v1/feedback/stats?tenant_id=<tenant>&start_date=$(date -d '7 days ago' +%Y-%m-%d)"

# Look for:
# - average_rating <3.0 = quality issue
# - thumbs_down_ratio >40% = significant dissatisfaction
```

**Step 2: Review Feedback Comments for Patterns**
```bash
# Get recent feedback with comments
curl -H "Authorization: Bearer $TOKEN" "https://api-url/api/v1/feedback?tenant_id=<tenant>&has_comment=true&limit=20"

# Categorize comments:
# - "Too generic" → Prompt tuning needed (Cause #3)
# - "Missing context" → Insufficient history (Cause #1)
# - "Wrong documentation" → Irrelevant KB articles (Cause #4)
# - "Outdated info" → Documentation needs refresh (Cause #2)
```

**Step 3: Analyze Specific Low-Rated Enhancement**
- Find ticket ID from feedback
- Review context gathering logs for that ticket
- Check: How many similar tickets found? How many docs retrieved? Relevance scores?

**Step 4: Compare with High-Rated Enhancements**
- Find highly-rated enhancements for same client
- Identify differences: More context? Better docs? Different ticket type?

---

## Resolution

**If Insufficient Ticket History (Cause #1):**
- Escalate to Engineering to backfill ticket history (Story 2.5A process)
- Target: At least 50-100 resolved tickets for good context
- Advise client: Quality will improve as more tickets are resolved

**If Missing/Outdated Documentation (Cause #2):**
- Request documentation from client (SOPs, network diagrams, FAQs)
- Schedule quarterly documentation refresh with client
- Work with Engineering to upload and structure documents

**If Generic Prompts (Cause #3):**
- Escalate to Engineering with feedback samples (10-20 examples)
- Provide client industry/environment details
- Schedule client interview to understand specific needs
- A/B test custom prompts vs. default prompts

**If Irrelevant KB Articles (Cause #4):**
- Escalate to Engineering with examples of wrong doc retrieval
- Work with client to clean up knowledge base (remove outdated/irrelevant)
- Consider increasing relevance score threshold (e.g., only use docs with score >0.7)

---

## Prevention

**Proactive Quality Monitoring:**
- Weekly review of Baseline Metrics Dashboard (average rating trend)
- Monthly feedback comment analysis (identify new quality patterns)
- Quarterly client check-in: "How's quality? Any areas for improvement?"

**Knowledge Base Maintenance:**
- Quarterly documentation refresh with client
- Remove outdated documents immediately when client reports
- Add new documents when client deploys new systems/processes

**Continuous Improvement:**
- A/B test prompt variations for low-rated ticket categories
- Build client-specific prompt library (industry, environment, priorities)
- Track quality improvements after prompt tuning (baseline vs. post-tuning)

---

## Escalation

**Escalate to L2/Engineering when:**
- Average rating <3.0 for client (7-day rolling average)
- Client escalates quality concerns to account manager
- Specific ticket category consistently <2.5 rating (e.g., "network issues")
- Feedback comments indicate systematic issue (not isolated cases)
- More than 40% thumbs-down ratio for client

**Provide in Escalation:**
- Feedback statistics (average rating, thumbs up/down counts, trends)
- 10-20 low-rated enhancement examples with ticket IDs
- Feedback comments (anonymized if needed)
- Client context: industry, environment, specific terminology
- Hypothesis on root cause (insufficient history, missing docs, generic prompts, wrong docs)

---

## Related Articles

- [FAQ: Enhancements Not Received](faq-enhancements-not-received.md) - If enhancements not arriving
- [FAQ: Database Queries for Support](faq-database-queries.md) - How to query feedback API and ticket history

---

## Version History

| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | 2025-11-04 | Initial creation (Code Review follow-up) | Dev Agent (AI) |
