# User Interview Script - Next.js UI Migration

**Project:** AI Agents Platform Next.js UI Migration
**Interview Duration:** 45-60 minutes
**Format:** 1-on-1, recorded (with permission)
**Interviewer:** Ravi / Product Team

---

## Interview Objectives

1. Understand current Streamlit UI pain points
2. Identify most-used features and workflows
3. Discover mobile/remote usage patterns
4. Gather design preferences (light vs dark, layout, navigation)
5. Prioritize features for Next.js UI
6. Create user personas based on real usage

---

## Pre-Interview Checklist

- [ ] Schedule 1-hour Zoom/Meet call
- [ ] Send calendar invite with agenda
- [ ] Request permission to record
- [ ] Prepare screen sharing (show Streamlit UI)
- [ ] Have note-taking doc ready

---

## Interview Structure

### Part 1: Introduction (5 min)
### Part 2: Current Experience (15 min)
### Part 3: Pain Points (10 min)
### Part 4: Feature Prioritization (10 min)
### Part 5: Design Preferences (5 min)
### Part 6: Mobile & Remote Usage (5 min)
### Part 7: Wrap-up (5 min)

---

## Part 1: Introduction (5 min)

**Say:**
> Hi [Name]! Thanks for taking the time to chat with me today. We're planning to migrate the AI Agents Platform from Streamlit to a new Next.js UI, and I want to make sure we build something that actually solves your problems and makes your job easier.
>
> This interview will take about 45-60 minutes. I'll be asking about your current experience with the platform, pain points, and what features are most important to you.
>
> There are no right or wrong answers - I'm just trying to understand how you use the platform today. Is it okay if I record this session so I can review it later? (The recording is just for our team and won't be shared publicly.)

**Ask:**
1. Can you briefly introduce yourself and your role?
2. How long have you been using the AI Agents Platform?
3. How often do you use it? (Daily, weekly, occasionally?)

**Notes:**
- Record role (super_admin, tenant_admin, operator, developer, viewer)
- Record usage frequency
- Build rapport, make them comfortable

---

## Part 2: Current Experience with Streamlit UI (15 min)

**Ask:**

1. **"Walk me through a typical workflow when you use the platform. What do you do from start to finish?"**
   - *Goal: Understand primary use cases*
   - *Listen for: Which pages they use, in what order, how often*

2. **"Which features or pages do you use most frequently?"**
   - *Goal: Identify must-have features*
   - *Prompt if needed:* Dashboard? Agents? Executions? Queue? Tenants?

3. **"Are there any features you rarely or never use?"**
   - *Goal: Identify low-priority features*
   - *Follow-up:* Why don't you use them?

4. **"How do you typically navigate between different sections?"**
   - *Goal: Understand navigation patterns*
   - *Observe: Do they use sidebar, search, back button?*

5. **"Do you ever have multiple tasks running at once? How do you keep track of them?"**
   - *Goal: Understand multitasking needs*

**Notes:**
- Screen share Streamlit UI if helpful
- Ask them to show their workflow (if possible)
- Note which pages get mentioned most

---

## Part 3: Pain Points & Frustrations (10 min)

**Ask:**

1. **"What frustrates you most about the current UI?"**
   - *Goal: Identify biggest pain points*
   - *Listen for: Performance, navigation, design, usability*

2. **"Are there any tasks that take longer than they should? Why?"**
   - *Goal: Identify efficiency blockers*
   - *Examples: Too many clicks, slow loading, hard to find info*

3. **"Have you ever struggled to find something in the UI?"**
   - *Goal: Identify navigation/IA issues*
   - *Follow-up:* What were you looking for?

4. **"Are there any features that are confusing or hard to use?"**
   - *Goal: Identify usability issues*

5. **"If you could fix one thing about the current UI, what would it be?"**
   - *Goal: Prioritize top pain point*

**Notes:**
- Listen for recurring themes (performance, navigation, mobile)
- Ask for specific examples
- Don't defend current UI - just listen and learn

---

## Part 4: Feature Prioritization (10 min)

**Say:**
> Now I'm going to show you a list of features from the current Streamlit UI. I'd like you to rate each one based on how important it is to YOUR daily work.

**Show List (share screen):**

| Feature | Importance (1-5) | Notes |
|---------|------------------|-------|
| Dashboard (metrics overview) | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Agent Performance (charts) | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| LLM Costs Tracking | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Worker Status | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Tenant Management | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Agent Configuration | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| LLM Provider Setup | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| MCP Server Management | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Queue Management | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Execution History | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Audit Logs | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Plugin Management | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| System Prompts | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |
| Add Tool (OpenAPI) | ☐ 1 ☐ 2 ☐ 3 ☐ 4 ☐ 5 |  |

**Ask:**
1. **"Which features do you use multiple times per day?"** (Rate 5)
2. **"Which features do you use a few times per week?"** (Rate 3-4)
3. **"Which features do you rarely use?"** (Rate 1-2)
4. **"Are there any features missing that you wish existed?"**

**Notes:**
- Record scores for each feature
- Ask for clarification on why certain features are important/unimportant
- Note feature requests

---

## Part 5: Design Preferences (5 min)

**Ask:**

1. **"Do you prefer light mode or dark mode? Why?"**
   - *Goal: Validate design system theme*
   - *Current: Light theme with Liquid Glass design*

2. **"How important is mobile access to you?"**
   - *Goal: Prioritize responsive design*
   - *Follow-up:* What would you do on mobile vs desktop?

3. **"Do you have any design preferences or examples of UIs you really like?"**
   - *Goal: Gather design inspiration*
   - *Examples: Other tools, apps, websites*

4. **"Show 2-3 design mockups: Which do you prefer and why?"**
   - *Show existing `.superdesign` mockups*
   - *Goal: Validate visual direction*

**Notes:**
- Note theme preferences (most users should prefer light)
- Note UI examples they mention
- Record mockup feedback

---

## Part 6: Mobile & Remote Usage (5 min)

**Ask:**

1. **"Do you ever access the platform from a mobile device? (Phone, tablet)**
   - *If yes:* How often? What do you do on mobile?
   - *If no:* Would you want to? What use cases?

2. **"Do you work remotely or from different locations?"**
   - *Goal: Understand access patterns*

3. **"Have you ever needed to check something urgently while away from your desk?"**
   - *Goal: Identify mobile use cases*
   - *Examples: Check queue status, pause system, view alerts*

4. **"What features would be most useful on mobile?"**
   - *Goal: Prioritize mobile features*
   - *Likely: Dashboard, alerts, queue control*

**Notes:**
- Record mobile usage frequency
- Note mobile use cases
- Identify mobile-critical features

---

## Part 7: Wrap-up (5 min)

**Ask:**

1. **"Is there anything else you'd like to share about your experience with the platform?"**
   - *Goal: Catch anything we missed*

2. **"Would you be interested in testing the new UI before it launches? (Beta program)"**
   - *Goal: Recruit beta testers*

3. **"Can I follow up with you if I have more questions?"**
   - *Goal: Leave door open for clarifications*

**Say:**
> Thank you so much for your time! This feedback is incredibly valuable. We'll use it to build a UI that actually makes your job easier. I'll keep you posted on progress, and we'll definitely reach out when we have something for you to test.

**Notes:**
- Ask for beta tester consent
- Get contact info for follow-up
- Thank them sincerely

---

## Post-Interview Checklist

- [ ] Save recording
- [ ] Review and clean up notes
- [ ] Extract key quotes
- [ ] Identify recurring themes
- [ ] Add findings to synthesis doc
- [ ] Send thank-you email

---

## Interview Notes Template

Copy this template for each interview:

```
INTERVIEW NOTES - [Name] - [Date]

=== PARTICIPANT INFO ===
Name:
Role:
RBAC Role (super_admin/tenant_admin/operator/developer/viewer):
Usage Frequency:

=== WORKFLOW ===
Primary use cases:
-
-

Most-used features (in order):
1.
2.
3.

Rarely-used features:
-
-

=== PAIN POINTS ===
Top frustrations:
1.
2.
3.

Tasks that take too long:
-

Navigation issues:
-

=== FEATURE PRIORITIES ===
Must-have (5/5):
-
-

Important (3-4/5):
-
-

Nice-to-have (1-2/5):
-

Missing features:
-

=== DESIGN PREFERENCES ===
Light vs Dark:
Mobile usage:
Favorite UIs:
Mockup feedback:

=== MOBILE USAGE ===
Mobile frequency:
Mobile use cases:
Mobile-critical features:

=== QUOTES ===
"..." - about [topic]

=== ACTION ITEMS ===
- Follow-up question:
- Beta tester: Yes/No

=== SYNTHESIS ===
Persona match: [Super Admin Sarah / Tenant Admin Tom / etc.]
Key insights:
-
-

```

---

## Analysis Guidelines

**After 5-8 interviews:**

1. **Create affinity map:**
   - Group similar pain points
   - Identify patterns across users
   - Count frequency of mentions

2. **Prioritize features:**
   - Average importance scores
   - Weight by user role
   - Create prioritized backlog

3. **Create personas:**
   - Group users by role and behavior
   - 1 persona per RBAC role (5 total)
   - Include: Goals, Pain Points, Usage Patterns, Tech Comfort

4. **Document findings:**
   - Write `user-research-findings.md`
   - Include: Themes, Quotes, Recommendations
   - Share with team

---

**Interviewer Tips:**

- ✅ **DO:** Listen more than you talk (80/20 rule)
- ✅ **DO:** Ask "why" and "tell me more"
- ✅ **DO:** Let silence happen (they'll fill it)
- ✅ **DO:** Take notes on exact quotes
- ❌ **DON'T:** Lead the witness ("Don't you think X is slow?")
- ❌ **DON'T:** Defend the current UI
- ❌ **DON'T:** Interrupt their answers
- ❌ **DON'T:** Skip uncomfortable topics

---

**Good luck with the interviews!** 🎙️
