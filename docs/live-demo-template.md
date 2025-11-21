# Live Demo - AI Agents Platform (Next.js UI)

**Version:** 1.0 | **Date:** January 2025 | **Duration:** 30 minutes | **Format:** Zoom

---

## Meeting Details

**Title:** AI Agents Platform - Next.js UI Live Demo

**Date & Time:** [To be scheduled 1 week before GA launch]
- **Suggested:** [DATE], [TIME] [TIMEZONE]
- **Example:** Tuesday, January 28, 2025, 10:00 AM - 10:30 AM PST

**Platform:** Zoom

**Zoom Link:** [To be generated and inserted here]

**Meeting ID:** [Zoom meeting ID]

**Passcode:** [Zoom passcode]

**Calendar Invite:** [Attach .ics file or Google Calendar link]

---

## Attendees

### Required Attendees
- [ ] **Operations Team** (All members) - Primary users of the platform
- [ ] **Product Owner** (Ravi) - Requirements owner
- [ ] **Scrum Master** (Bob) - Workflow facilitator

### Optional Attendees
- [ ] **Development Team** - Available for Q&A
- [ ] **Support Team** - Learn platform for user support
- [ ] **Management** - Stakeholder visibility

**RSVP:** [Google Form link or email to RSVP]

**Target Attendance:** 10-15 people

---

## Agenda (30 minutes)

### Segment 1: Introduction (5 minutes)
**Presenter:** Product Owner (Ravi) or Scrum Master (Bob)

**Topics:**
1. **Welcome & Overview** (1 minute)
   - Purpose of the demo
   - Why we built the new UI (replacing Streamlit)
   - What to expect in the next 30 minutes

2. **Project Background** (2 minutes)
   - Epic 4: Next.js UI Migration
   - 9 stories completed (Stories 0-8)
   - GA launch timeline (1 week from today)

3. **Key Benefits** (2 minutes)
   - 80% faster page load (< 2s vs 5-8s)
   - Modern design (Apple Liquid Glass aesthetic)
   - Mobile-responsive (works on phones and tablets)
   - Enhanced security (JWT authentication, RBAC)
   - Real-time updates (auto-refresh dashboards)

**Slides:** 3 slides (Welcome, Project Background, Key Benefits)

---

### Segment 2: Live Walkthrough (15 minutes)
**Presenter:** Technical Lead or Developer

**Demo Script:**

#### 2.1: Login & Authentication (2 minutes)
- Show login page at `/auth/login`
- Enter credentials → Dashboard appears
- Highlight: "Secure JWT authentication with role-based access control"

#### 2.2: Dashboard Overview (3 minutes)
- Show 4 metric cards (Active Agents, Pending Tasks, Avg Response Time, Success Rate)
- Highlight: "Auto-refreshes every 5 seconds (no manual refresh needed)"
- Scroll to activity feed and charts
- Show tenant switcher in header
- Click tenant switcher → Search for tenant → Select → Dashboard updates instantly

#### 2.3: Navigation & New Features (3 minutes)
- Show sidebar menu (4 categories: Monitoring, Configuration, Operations, Tools)
- Press `Cmd+K` → Show command palette (fuzzy search)
- Press `Cmd+D` → Toggle dark mode
- Show mobile view (resize browser or show on phone)
- Highlight: "Fully keyboard-navigable, mobile-responsive, dark mode support"

#### 2.4: Creating an Agent (3 minutes)
- Click "Configuration" → "Agents" → "+ New Agent"
- Fill in form:
  - Name: "Demo Agent"
  - System Prompt: "You are a helpful assistant"
  - LLM Provider: "OpenAI GPT-4"
- Click "Save" → Agent appears in table
- Highlight: "Optimistic UI updates (instant feedback, automatic rollback on error)"

#### 2.5: Testing an Agent (2 minutes)
- Click on "Demo Agent" → Click "Test"
- Enter test input: "What is 2+2?"
- Click "Run Test" → Output appears: "4"
- Highlight: "Live test sandbox with real-time execution"

#### 2.6: Execution History & Advanced Features (2 minutes)
- Click "Operations" → "Execution History"
- Show filters (status, date range, agent)
- Click "Export CSV"
- Show sortable columns, pagination
- Highlight: "Enhanced data tables with TanStack Table v8"

**Demo Environment:**
- Use **staging environment** (not production) with demo data
- Pre-populate database with 5-10 agents, 20+ executions
- Ensure no real customer data is visible

---

### Segment 3: Q&A (8 minutes)
**Moderator:** Scrum Master (Bob)

**Expected Questions:**

**Q1: When will this be available?**
**A:** GA launch is scheduled for [DATE], 1 week from today. You'll receive an email with login instructions.

**Q2: Do we need to do anything to prepare?**
**A:** Contact your admin for login credentials. Review the Quick Start Guide (1-page PDF) and watch the 5-minute video walkthrough (links in the email).

**Q3: Will the old Streamlit UI still work?**
**A:** Yes, for 2 weeks after GA launch, Streamlit will be accessible at `/admin-legacy` (read-only mode). After 2 weeks, it will redirect to the Next.js UI.

**Q4: What if I encounter issues?**
**A:** We have 3 runbooks for common issues:
- Login issues (`docs/runbooks/login-issues.md`)
- Performance issues (`docs/runbooks/performance-issues.md`)
- Data sync issues (`docs/runbooks/data-sync-issues.md`)

Also, use the in-app feedback widget (💬 button) or contact support.

**Q5: Can I still use my existing workflows?**
**A:** Yes, all functionality from Streamlit is available in Next.js. See the migration guide for page mapping (14 Streamlit pages → Next.js routes).

**Q6: What about mobile access?**
**A:** Fully supported! Works on iPhone, iPad, Android phones and tablets. Bottom navigation, swipe gestures, touch-optimized buttons.

**Q7: Will my role change?**
**A:** Your role (super_admin, tenant_admin, operator, developer, viewer) determines what you can do. Check with your admin if you need a different role.

**Q8: How do I report bugs or request features?**
**A:** Click the "💬 Feedback" button in the UI → Select sentiment → Describe the issue → Submit. Your feedback goes directly to the product team.

**Open Q&A:** Allow attendees to ask additional questions (5 minutes)

---

### Segment 4: Wrap-Up & Next Steps (2 minutes)
**Presenter:** Product Owner (Ravi) or Scrum Master (Bob)

**Topics:**
1. **Thank You** (30 seconds)
   - Appreciate everyone's time
   - Excited to launch next week

2. **Next Steps** (1 minute)
   - Watch for GA launch email ([DATE])
   - Review Quick Start Guide and video walkthrough
   - Attend optional training session (if scheduled)
   - Test the platform in your workflow

3. **Support Resources** (30 seconds)
   - Quick Start Guide: `docs/quick-start-guide.pdf`
   - Video Walkthrough: `docs/video-walkthrough.md` (5 minutes)
   - Migration Guide: `docs/migration-guide.md`
   - Runbooks: `docs/runbooks/` (login, performance, data sync issues)
   - API Docs: `/api/v1/docs` (for developers)
   - Support Email: support@aiagents.example.com (placeholder)
   - Slack: #ai-agents-support

**Closing:** "See you all on the new platform next week! 🚀"

---

## Preparation Checklist

### 1 Week Before Demo
- [ ] **Schedule meeting** (1 week before GA launch)
- [ ] **Send calendar invites** to all attendees
- [ ] **Create Zoom meeting** (30 minutes, enable waiting room, record to cloud)
- [ ] **Prepare slides** (3 slides: Welcome, Background, Benefits)
- [ ] **Set up staging environment** with demo data
- [ ] **Test all demo actions** (dry run)
- [ ] **Prepare Q&A talking points** (review FAQs)

### 3 Days Before Demo
- [ ] **Send reminder email** with agenda and Zoom link
- [ ] **Upload slides** to shared drive (backup)
- [ ] **Test Zoom screen sharing** and audio
- [ ] **Assign roles** (Presenter, Moderator, Q&A responder)

### 1 Day Before Demo
- [ ] **Final dry run** (full 30-minute walkthrough)
- [ ] **Verify demo data** in staging environment
- [ ] **Test Zoom recording** (start/stop, cloud storage)
- [ ] **Print agenda** (for reference during live demo)

### Day of Demo
- [ ] **Join Zoom 15 minutes early** (test audio/video)
- [ ] **Open all demo tabs** in browser (pre-load pages)
- [ ] **Close unnecessary applications** (reduce distractions)
- [ ] **Start recording** when meeting begins
- [ ] **Share screen** (full screen, hide desktop icons)

---

## Meeting Invitation Template

### Email Subject
```
[INVITE] AI Agents Platform - Next.js UI Live Demo | [DATE] at [TIME]
```

### Email Body
```
Hi Team,

You're invited to a live demo of the new AI Agents Platform Next.js UI, launching next week!

📅 **When:** [DATE], [TIME] [TIMEZONE]
⏱️ **Duration:** 30 minutes (20 min demo, 10 min Q&A)
🔗 **Zoom Link:** [Zoom URL]

**What to Expect:**
- Live walkthrough of the new UI (replacing Streamlit)
- Key features: Dashboard, Agent Management, Execution History, and more
- Mobile demo (iPhone, iPad)
- Q&A session

**Why Attend:**
- Learn how to navigate the new platform
- See new features (tenant switcher, dark mode, command palette)
- Ask questions before GA launch

**Agenda:**
1. Introduction (5 min) - Project background and key benefits
2. Live Walkthrough (15 min) - Dashboard, create agent, test, execution history
3. Q&A (8 min) - Your questions answered
4. Wrap-Up (2 min) - Next steps and support resources

**Pre-Read (Optional):**
- Quick Start Guide: [Link to PDF]
- Video Walkthrough: [Link to 5-min Loom video]
- Migration Guide: [Link to docs/migration-guide.md]

**Can't Attend?**
Recording will be available in the shared drive within 24 hours.

**RSVP:** [Google Form link or "Reply to this email"]

Looking forward to seeing you there! 🚀

Best,
[Your Name]
[Your Title]
```

---

## Zoom Meeting Settings

### General Settings
- [ ] **Meeting Type:** Scheduled Meeting
- [ ] **Duration:** 30 minutes
- [ ] **Timezone:** [Your timezone]
- [ ] **Recurring meeting:** No

### Security Settings
- [ ] **Require meeting passcode:** Yes
- [ ] **Waiting room:** Enabled (admit attendees before start)
- [ ] **Only authenticated users can join:** No (allow guests)
- [ ] **Lock meeting after start:** No (late arrivals allowed)

### Audio/Video Settings
- [ ] **Audio:** Computer Audio (VoIP)
- [ ] **Video:** Host and participants can turn on video
- [ ] **HD video:** Enabled (for clear screen sharing)

### Recording Settings
- [ ] **Record meeting:** Automatically record to cloud
- [ ] **Recording layout:** Active speaker view with shared screen
- [ ] **Record separate audio:** Yes (for post-editing if needed)

### Screen Sharing Settings
- [ ] **Who can share:** Host only (presenter shares screen)
- [ ] **Disable participant screen sharing:** Yes (avoid disruptions)

### Advanced Settings
- [ ] **Enable live transcription:** Yes (auto-generated captions)
- [ ] **Enable Q&A:** Yes (for structured Q&A)
- [ ] **Enable chat:** Yes (for questions during demo)
- [ ] **Enable reactions:** Yes (👍 for engagement)

---

## Post-Demo Tasks

### Immediately After Demo (Same Day)
- [ ] **Stop recording** and verify cloud upload
- [ ] **Export Q&A transcript** from Zoom (if Q&A feature used)
- [ ] **Export chat log** (for questions not answered live)
- [ ] **Send thank you email** with recording link and slides

### Within 24 Hours
- [ ] **Share recording** on shared drive (Google Drive / SharePoint)
- [ ] **Create follow-up email** with:
  - Recording link
  - Slides (PDF)
  - Quick Start Guide (PDF)
  - Video Walkthrough (Loom)
  - GA launch date reminder
- [ ] **Update FAQ** with new questions from Q&A
- [ ] **Schedule optional training session** (if needed)

### Within 3 Days
- [ ] **Review attendance** (who attended, who missed)
- [ ] **Send recording to no-shows** (individual emails)
- [ ] **Collect feedback** (Google Form: "Was the demo helpful? What could be improved?")
- [ ] **Update runbooks** with new common issues from Q&A

---

## Backup Plan (If Technical Issues)

### Issue 1: Zoom Connection Fails
**Backup:** Use Google Meet or Microsoft Teams
- [ ] Pre-create backup meeting link (Google Meet)
- [ ] Email backup link to attendees 1 day before demo

### Issue 2: Screen Sharing Not Working
**Backup:** Use pre-recorded video
- [ ] Record demo in advance (backup video)
- [ ] Play video if live screen sharing fails
- [ ] Narrate over video

### Issue 3: Staging Environment Down
**Backup:** Use production with read-only account
- [ ] Create demo account with viewer role (read-only)
- [ ] Use production environment (no edits, just viewing)

### Issue 4: Presenter Unavailable (Last Minute)
**Backup:** Assign backup presenter
- [ ] Primary Presenter: [Name]
- [ ] Backup Presenter #1: [Name]
- [ ] Backup Presenter #2: [Name]

---

## Success Metrics

### Quantitative Metrics
- **Attendance Rate:** Target 80% of invitees (e.g., 12 out of 15)
- **Engagement Rate:** Target 50% of attendees ask questions or react
- **Recording Views:** Target 90% of no-shows watch recording within 1 week

### Qualitative Metrics
- **Feedback Score:** Target 4.5+ out of 5 (post-demo survey)
- **Top Feedback Themes:** Note common questions and concerns (improve docs)

### Post-Demo Survey Questions
1. How helpful was the demo? (1-5 scale)
2. What feature are you most excited about?
3. What concerns do you have about the migration?
4. Would you like additional training? (Yes/No)
5. Any other comments or questions?

---

## Calendar Invite (.ics File)

**To generate .ics file:**

Use online tool (https://ical.marudot.com/) or create manually:

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Agents Platform//Live Demo//EN
BEGIN:VEVENT
UID:live-demo-nextjs-ui@aiagents.example.com
DTSTAMP:20250128T100000Z
DTSTART:20250128T180000Z
DTEND:20250128T183000Z
SUMMARY:AI Agents Platform - Next.js UI Live Demo
DESCRIPTION:Live demo of the new AI Agents Platform Next.js UI.\n\nAgenda:\n- Introduction (5 min)\n- Live Walkthrough (15 min)\n- Q&A (8 min)\n- Wrap-Up (2 min)\n\nZoom Link: [Zoom URL]\nMeeting ID: [Meeting ID]\nPasscode: [Passcode]\n\nPre-Read:\n- Quick Start Guide: [Link]\n- Video Walkthrough: [Link]
LOCATION:[Zoom URL]
STATUS:CONFIRMED
SEQUENCE:0
BEGIN:VALARM
TRIGGER:-PT15M
DESCRIPTION:Reminder: AI Agents Platform Live Demo starts in 15 minutes
ACTION:DISPLAY
END:VALARM
END:VEVENT
END:VCALENDAR
```

**Attach .ics file to email** for easy calendar import.

---

**Generated by:** Bob (Scrum Master)
**Date:** January 2025
**Version:** 1.0

**Status:** 📅 Ready to schedule

---

## Notes for Presenter

**Presentation Tips:**
- ✅ Speak slowly and clearly (pause between actions)
- ✅ Use cursor to highlight UI elements (circles, underlines)
- ✅ Zoom in if text is small (200% zoom for key UI elements)
- ✅ Avoid jargon (explain technical terms)
- ✅ Smile and maintain positive energy (this is exciting!)

**Common Mistakes to Avoid:**
- ❌ Talking too fast (rushing through the demo)
- ❌ Skipping steps (assume everyone is familiar with the platform)
- ❌ Not checking chat (missing questions during demo)
- ❌ Going over time (stick to 30 minutes total)

**Pro Tips:**
- ✅ Mute yourself when not speaking (reduces background noise)
- ✅ Ask attendees to use "raise hand" feature for questions
- ✅ Summarize questions before answering (ensure everyone heard)
- ✅ End 2 minutes early (allow buffer for overrun)
