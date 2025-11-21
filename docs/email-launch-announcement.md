# Pre-Launch Email - AI Agents Platform (Next.js UI)

**Version:** 1.0 | **Date:** January 2025 | **Audience:** All platform users (Operations Team)

---

## Email #1: GA Launch Announcement (1 Week Before)

### Subject Line Options

**Option A (Friendly):**
```
🚀 New AI Agents Platform UI Launching Next Week - Get Ready!
```

**Option B (Professional):**
```
AI Agents Platform - Next.js UI GA Launch | [DATE] | Action Required
```

**Option C (Urgency):**
```
Important: New Platform UI Goes Live [DATE] - Login Credentials Inside
```

**Recommended:** Option A (friendly, emoji for visibility)

---

### Email Body (1 Week Before)

```
Subject: 🚀 New AI Agents Platform UI Launching Next Week - Get Ready!

Hi Team,

Great news! The new AI Agents Platform UI is launching **[DATE]** and it's a massive upgrade from the old Streamlit interface.

**What's New?**
✨ 80% faster page load (< 2 seconds vs 5-8 seconds)
🎨 Modern Apple-inspired design (Liquid Glass aesthetic)
📱 Fully mobile-responsive (works on phones and tablets)
🔐 Enhanced security (JWT authentication, role-based access control)
⚡ Real-time auto-refresh (dashboards update every 5 seconds)
🌙 Dark mode support (toggle with Cmd+D)
⌨️ Keyboard shortcuts (Cmd+K for command palette)

**When Does It Launch?**
📅 **GA Launch:** [DATE], [TIME] [TIMEZONE]

**What Do I Need to Do?**

1. **Get Your Login Credentials**
   - If you already have an account: No action needed, use your existing email and password
   - If you're new: Contact [ADMIN NAME] at [ADMIN EMAIL] for account creation

2. **Review the Quick Start Guide** (5 minutes)
   📄 Download: [Link to quick-start-guide.pdf]
   - Learn how to log in, navigate, and use key features

3. **Watch the Video Walkthrough** (5 minutes)
   🎥 Watch: [Link to Loom video]
   - See the platform in action with a guided tour

4. **Bookmark the New URL**
   🔗 New URL: https://your-domain.com/dashboard
   - The old Streamlit UI (`/admin`) will redirect to `/admin-legacy` (read-only for 2 weeks)

**Optional: Attend the Live Demo**
📅 **When:** [DATE], [TIME] [TIMEZONE] (30 minutes)
🔗 **Zoom Link:** [Zoom URL]
**Agenda:** Live walkthrough, Q&A, next steps

**Can't attend?** Recording will be shared within 24 hours.

**Support Resources**
📚 Migration Guide: [Link to migration-guide.md]
📝 Changelog: [Link to changelog.md]
🔧 Runbooks: [Link to docs/runbooks/] (troubleshooting common issues)
💬 In-App Feedback: Click "💬 Feedback" button in the UI
✉️ Email Support: support@aiagents.example.com

**What Happens to the Old Streamlit UI?**
- **For 2 weeks:** Accessible at `/admin-legacy` (read-only mode)
- **After 2 weeks:** Redirects permanently to Next.js UI

**Questions?**
Reply to this email or join our Slack channel: #ai-agents-support

Looking forward to seeing you on the new platform next week! 🚀

Best,
[Your Name]
[Your Title]
AI Agents Platform Team

---

**P.S.** Here's a sneak peek of the new Dashboard:
[Attach dashboard screenshot: dashboard-preview.png]
```

---

## Email #2: GA Launch Day (Day Of)

### Subject Line
```
✅ AI Agents Platform - New UI is Now Live!
```

---

### Email Body (Day Of)

```
Subject: ✅ AI Agents Platform - New UI is Now Live!

Hi Team,

The new AI Agents Platform UI is **NOW LIVE**! 🎉

**Access the Platform:**
🔗 https://your-domain.com/dashboard

**Login Instructions:**
1. Go to: https://your-domain.com/auth/login
2. Enter your email and password
3. Click "Log in" → Dashboard appears

**First Time Logging In?**
- If you don't have credentials, contact [ADMIN NAME] at [ADMIN EMAIL]
- If you forgot your password, click "Forgot password?" on the login page

**Quick Start (5 Minutes):**
1. Log in at `/auth/login`
2. Explore the Dashboard (auto-refreshes every 5 seconds)
3. Try the tenant switcher (top-right dropdown)
4. Press `Cmd+K` to open the command palette (fuzzy search)
5. Press `Cmd+D` to toggle dark mode

**Page Mapping (Streamlit → Next.js):**
| Old (Streamlit) | New (Next.js) | URL |
|-----------------|---------------|-----|
| Dashboard | Monitoring → Dashboard | `/dashboard` |
| Agent Management | Configuration → Agents | `/agents` |
| Execution History | Operations → Execution History | `/execution-history` |
| Operations | Operations → Queue Management | `/operations` |
| Workers | Monitoring → Workers | `/workers` |

**Full page mapping:** [Link to migration-guide.md]

**Need Help?**
📚 **Quick Start Guide:** [Link to PDF]
🎥 **Video Walkthrough:** [Link to Loom video]
🔧 **Runbooks:** [Link to docs/runbooks/]
   - Login issues
   - Performance issues
   - Data sync issues
💬 **In-App Feedback:** Click "💬 Feedback" button
✉️ **Email Support:** support@aiagents.example.com
💬 **Slack:** #ai-agents-support

**Known Issues:**
⚠️ If you see "Token expired. Please log in again" → This is normal if you were testing the beta. Just log in again.
⚠️ If you see "You don't have permission" → Check your role with your admin. Some actions require higher permissions.

**Streamlit UI (Old):**
- Still accessible at `/admin-legacy` for **2 weeks** (read-only mode)
- After 2 weeks (February 11, 2025), it will redirect to Next.js UI

**Feedback:**
We'd love to hear your thoughts! Click the "💬 Feedback" button in the UI or reply to this email.

Thanks for your patience during this migration. Enjoy the new platform! 🚀

Best,
[Your Name]
[Your Title]
AI Agents Platform Team

---

**Attachments:**
- quick-start-guide.pdf (1-page reference)
- keyboard-shortcuts-cheatsheet.pdf (optional)
```

---

## Email #3: Follow-Up (1 Day After Launch)

### Subject Line
```
👋 How's the New Platform? Feedback Needed
```

---

### Email Body (1 Day After Launch)

```
Subject: 👋 How's the New Platform? Feedback Needed

Hi Team,

The new AI Agents Platform UI has been live for 24 hours! How's it going? 🤔

**Quick Check-In:**
1. ✅ Were you able to log in successfully?
2. ✅ Did you find the features you need?
3. ✅ Any issues or confusion?

**We Want Your Feedback!**
📝 **Take 2-minute survey:** [Google Form link]
- What do you like?
- What needs improvement?
- Any bugs or issues?

**OR** Click the "💬 Feedback" button in the UI (bottom-right).

**Common Issues (and Fixes):**

**Issue 1: "I can't log in"**
✅ **Fix:**
- Ensure you're using your email (not username)
- Click "Forgot password?" to reset
- Contact [ADMIN NAME] if you don't have an account

**Issue 2: "The page is loading slowly"**
✅ **Fix:**
- Hard refresh: `Cmd+Shift+R` (Mac) or `Ctrl+Shift+R` (Windows)
- Disable browser extensions (try incognito mode)
- See runbook: `docs/runbooks/performance-issues.md`

**Issue 3: "I don't see my agents"**
✅ **Fix:**
- Check tenant switcher (top-right) → Ensure correct tenant selected
- See runbook: `docs/runbooks/data-sync-issues.md`

**Still Having Issues?**
Reply to this email or Slack us at #ai-agents-support.

**Support Resources (Reminder):**
📚 Quick Start Guide: [Link to PDF]
🎥 Video Walkthrough: [Link to Loom]
📝 Migration Guide: [Link to migration-guide.md]
🔧 Runbooks: [Link to docs/runbooks/]

Thanks for being patient with the migration! 🙏

Best,
[Your Name]
[Your Title]
AI Agents Platform Team
```

---

## Email #4: Streamlit Decommission Reminder (1 Week Before Shutdown)

### Subject Line
```
⚠️ Streamlit UI Shutting Down [DATE] - Switch to Next.js Now
```

---

### Email Body (1 Week Before Shutdown)

```
Subject: ⚠️ Streamlit UI Shutting Down [DATE] - Switch to Next.js Now

Hi Team,

This is a **final reminder** that the old Streamlit UI will be permanently shut down on **[DATE]** (1 week from today).

**What's Happening?**
📅 **Shutdown Date:** [DATE], [TIME] [TIMEZONE]
🔗 **Affected URL:** `/admin-legacy` (old Streamlit UI)

After this date:
- `/admin-legacy` will redirect to `/dashboard` (Next.js UI)
- All Streamlit functionality will be unavailable
- **Action Required:** Switch to Next.js UI now if you haven't already

**Are You Still Using Streamlit?**
If yes, please switch to Next.js UI **this week**. Here's how:

**Step 1: Log in to Next.js UI**
🔗 https://your-domain.com/auth/login

**Step 2: Update Your Bookmarks**
Replace:
- `/admin` → `/dashboard`
- `/admin-legacy` → `/dashboard`

**Step 3: Learn the New Navigation**
📚 Quick Start Guide: [Link to PDF]
🎥 Video Walkthrough: [Link to Loom]

**Page Mapping (Find Your Pages):**
| Old (Streamlit) | New (Next.js) | URL |
|-----------------|---------------|-----|
| Dashboard | Monitoring → Dashboard | `/dashboard` |
| Tenants | Configuration → Tenants | `/tenants` |
| Agent Management | Configuration → Agents | `/agents` |
| Execution History | Operations → Execution History | `/execution-history` |
| Operations | Operations → Queue Management | `/operations` |
| Workers | Monitoring → Workers | `/workers` |
| LLM Costs | Monitoring → LLM Costs | `/costs` |

**Full mapping:** [Link to migration-guide.md]

**Need Help?**
📧 Email: support@aiagents.example.com
💬 Slack: #ai-agents-support
📞 Call: [Phone number if available]

**Why Are We Shutting Down Streamlit?**
- Next.js UI is 80% faster (< 2s page load)
- Better security (JWT authentication, RBAC)
- Mobile-responsive (works on phones and tablets)
- Real-time updates (auto-refresh dashboards)
- Modern design (Apple Liquid Glass aesthetic)

**What If I Miss the Deadline?**
No worries! After [DATE], `/admin-legacy` will automatically redirect to `/dashboard`. Just log in with your credentials.

Thanks for your cooperation! 🙏

Best,
[Your Name]
[Your Title]
AI Agents Platform Team
```

---

## Email Templates Summary

| Email | Send Date | Subject | Purpose |
|-------|-----------|---------|---------|
| **Email #1** | 1 week before GA | 🚀 New Platform Launching Next Week | Announce GA launch, share resources, invite to live demo |
| **Email #2** | GA launch day | ✅ Platform is Now Live! | Login instructions, quick start, page mapping |
| **Email #3** | 1 day after GA | 👋 How's the New Platform? | Collect feedback, troubleshoot common issues |
| **Email #4** | 1 week before Streamlit shutdown | ⚠️ Streamlit Shutting Down [DATE] | Final reminder to switch to Next.js |

---

## Email Design (HTML Template)

For branded emails, use this HTML structure:

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>AI Agents Platform - GA Launch</title>
  <style>
    body {
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      line-height: 1.6;
      color: #333;
      max-width: 600px;
      margin: 0 auto;
      padding: 20px;
      background-color: #f5f5f5;
    }
    .email-container {
      background-color: #ffffff;
      border-radius: 8px;
      padding: 40px;
      box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
    }
    .header {
      text-align: center;
      margin-bottom: 30px;
    }
    .header h1 {
      font-size: 24px;
      margin: 0 0 10px 0;
      color: #1a1a1a;
    }
    .emoji {
      font-size: 48px;
      margin-bottom: 10px;
    }
    .cta-button {
      display: inline-block;
      background-color: #6366f1;
      color: #ffffff;
      padding: 12px 24px;
      text-decoration: none;
      border-radius: 6px;
      margin: 20px 0;
      font-weight: 600;
    }
    .cta-button:hover {
      background-color: #4f46e5;
    }
    .feature-list {
      list-style: none;
      padding: 0;
    }
    .feature-list li {
      padding: 8px 0;
      border-bottom: 1px solid #eee;
    }
    .footer {
      margin-top: 40px;
      text-align: center;
      font-size: 12px;
      color: #888;
    }
  </style>
</head>
<body>
  <div class="email-container">
    <div class="header">
      <div class="emoji">🚀</div>
      <h1>New AI Agents Platform UI Launching Next Week</h1>
      <p>Get ready for a massive upgrade!</p>
    </div>

    <p>Hi Team,</p>

    <p>Great news! The new AI Agents Platform UI is launching <strong>[DATE]</strong> and it's a massive upgrade from the old Streamlit interface.</p>

    <h2>What's New?</h2>
    <ul class="feature-list">
      <li>✨ 80% faster page load (< 2 seconds)</li>
      <li>🎨 Modern Apple-inspired design</li>
      <li>📱 Fully mobile-responsive</li>
      <li>🔐 Enhanced security (JWT auth, RBAC)</li>
      <li>⚡ Real-time auto-refresh</li>
      <li>🌙 Dark mode support</li>
    </ul>

    <a href="https://your-domain.com/dashboard" class="cta-button">Access Platform</a>

    <h2>What Do I Need to Do?</h2>
    <ol>
      <li>Get your login credentials (contact admin if needed)</li>
      <li>Review the Quick Start Guide (5 minutes)</li>
      <li>Watch the Video Walkthrough (5 minutes)</li>
      <li>Bookmark the new URL</li>
    </ol>

    <p><strong>Support Resources:</strong></p>
    <ul>
      <li>📚 Quick Start Guide: <a href="#">Download PDF</a></li>
      <li>🎥 Video Walkthrough: <a href="#">Watch Video</a></li>
      <li>📝 Migration Guide: <a href="#">Read Guide</a></li>
      <li>💬 In-App Feedback: Click "💬 Feedback" button</li>
    </ul>

    <p>Looking forward to seeing you on the new platform next week! 🚀</p>

    <p>Best,<br>
    [Your Name]<br>
    [Your Title]<br>
    AI Agents Platform Team</p>

    <div class="footer">
      <p>AI Agents Platform | support@aiagents.example.com</p>
      <p><a href="#">Unsubscribe</a> | <a href="#">Update Preferences</a></p>
    </div>
  </div>
</body>
</html>
```

**To use:**
1. Save as `email-template.html`
2. Replace placeholders: `[DATE]`, `[YOUR NAME]`, `[Links]`
3. Test in email client (Gmail, Outlook)
4. Send via email marketing tool (Mailchimp, SendGrid) or directly

---

## Attachment: Quick Start Guide (1-Page PDF)

**File:** `docs/quick-start-guide.pdf`

**How to Attach:**
1. Convert `docs/quick-start-guide.md` to PDF (see guide in that file)
2. Attach to email as `quick-start-guide.pdf`
3. File size should be < 1MB for easy downloading

---

## Attachment: Keyboard Shortcuts Cheatsheet (Optional)

**File:** `docs/keyboard-shortcuts-cheatsheet.pdf`

**Content:**
```markdown
# Keyboard Shortcuts Cheatsheet

| Shortcut | Action |
|----------|--------|
| `Cmd+K` (Mac) / `Ctrl+K` (Win) | Open command palette |
| `Cmd+D` (Mac) / `Ctrl+D` (Win) | Toggle dark mode |
| `?` | Show all shortcuts |
| `Esc` | Close modals/dialogs |
| `/` | Focus search input |
| Arrow keys | Navigate tables, dropdowns |

**Print this page and keep it at your desk for quick reference!**
```

**How to Create:**
1. Create `docs/keyboard-shortcuts-cheatsheet.md` with content above
2. Convert to PDF (1 page, landscape orientation)
3. Optionally attach to Email #1 or #2

---

## Email Distribution List

**To:** operations-team@aiagents.example.com (mailing list)

**BCC:** stakeholders@aiagents.example.com (optional, for visibility)

**Exclude:** External users, customers (this is internal-only migration)

**Total Recipients:** ~15-20 people (Operations Team)

---

## Email Tracking (Optional)

If using email marketing tool (Mailchimp, SendGrid), track:
- **Open Rate:** Target 90%+ (critical announcement)
- **Click-Through Rate (CTR):** Target 50%+ (for Quick Start Guide, Video links)
- **Reply Rate:** Track questions and concerns (respond within 4 hours)

---

## Success Criteria

**Email #1 (1 Week Before):**
- [ ] 90%+ open rate (critical announcement)
- [ ] 50%+ download Quick Start Guide
- [ ] 50%+ watch Video Walkthrough
- [ ] 80%+ attend live demo (or watch recording)

**Email #2 (Launch Day):**
- [ ] 95%+ open rate (launch announcement)
- [ ] 80%+ successful logins within 24 hours
- [ ] < 5 support tickets related to login issues

**Email #3 (1 Day After):**
- [ ] 70%+ open rate (follow-up)
- [ ] 50%+ complete feedback survey
- [ ] < 3 critical bugs reported (P0/P1)

**Email #4 (Streamlit Shutdown):**
- [ ] 95%+ open rate (final warning)
- [ ] 100% of users switched to Next.js before shutdown
- [ ] 0 support tickets after shutdown (everyone migrated)

---

**Generated by:** Bob (Scrum Master)
**Date:** January 2025
**Version:** 1.0

**Status:** ✉️ Ready to send (customize placeholders first)

---

## Customization Checklist

Before sending, replace these placeholders:

**Email #1 (1 Week Before):**
- [ ] `[DATE]` → Actual GA launch date
- [ ] `[TIME]` → Launch time
- [ ] `[TIMEZONE]` → Your timezone (e.g., PST, EST)
- [ ] `[ADMIN NAME]` → Name of admin who creates accounts
- [ ] `[ADMIN EMAIL]` → Admin's email
- [ ] `[Link to quick-start-guide.pdf]` → Actual link
- [ ] `[Link to Loom video]` → Actual Loom link
- [ ] `[Zoom URL]` → Actual Zoom meeting link
- [ ] `[Your Name]` → Your name
- [ ] `[Your Title]` → Your title

**Email #2 (Launch Day):**
- [ ] All placeholders from Email #1
- [ ] `https://your-domain.com` → Actual domain

**Email #3 (1 Day After):**
- [ ] `[Google Form link]` → Actual feedback survey link

**Email #4 (Streamlit Shutdown):**
- [ ] `[DATE]` → Streamlit shutdown date (2 weeks after GA)
- [ ] `[Phone number if available]` → Support phone (or remove if not available)
