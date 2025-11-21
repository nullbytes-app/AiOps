# Video Walkthrough - AI Agents Platform (Next.js UI)

**Version:** 1.0 | **Date:** January 2025 | **Duration:** 5 minutes | **Format:** Loom video

---

## Video Details

**Recording Platform:** Loom (2025)
**Resolution:** 1080p (1920x1080)
**Frame Rate:** 30fps
**File Size Target:** < 50MB
**Recording Type:** Screen + Camera (presenter in bottom-right bubble)

**Loom Features to Enable:**
- ✅ Auto-lighting (for low-light environments)
- ✅ Noise filter (for background noise reduction)
- ✅ Live rewind (pause/fix errors mid-recording)
- ✅ AI auto-generation (titles, summaries, chapters)
- ✅ Transcript editing (clean up auto-generated transcript)

**Video URL:** [To be recorded and uploaded to Loom, link inserted here]

---

## Script & Storyboard (5 minutes total)

### Segment 1: Introduction (30 seconds)
**On-screen:**
- Login page at `/auth/login`
- Presenter in bottom-right bubble

**Voiceover:**
> "Hi, I'm [Your Name], and welcome to the AI Agents Platform. This is our new Next.js UI, which replaces the old Streamlit interface. In the next 5 minutes, I'll show you how to navigate the platform, create an agent, test it, and view execution history. Let's get started."

**Actions:**
1. Show login page
2. Enter credentials: `demo@example.com` / `password`
3. Click "Log in" → Dashboard appears

**Visual Callouts:**
- Cursor highlights email field
- Cursor highlights password field
- Cursor highlights "Log in" button

**Timestamp:** 0:00 - 0:30

---

### Segment 2: Dashboard Overview (1 minute)
**On-screen:**
- Dashboard at `/dashboard`
- Show all 4 metric cards, activity feed, and charts

**Voiceover:**
> "After logging in, you land on the Dashboard. Here you can see key metrics: Active Agents, Pending Tasks, Average Response Time, and Success Rate. These metrics auto-refresh every 5 seconds, so you always have real-time data. Below, you can see the activity feed showing recent executions, and charts displaying trends over time."

**Actions:**
1. Hover over each metric card (highlight with cursor)
2. Scroll down to activity feed
3. Point to the line chart (execution trend)
4. Show the sidebar menu on the left

**Visual Callouts:**
- Highlight "Auto-refresh: 5s" badge (bottom-right)
- Zoom in on metric cards (20% zoom)
- Cursor circles the activity feed

**Timestamp:** 0:30 - 1:30

---

### Segment 3: Navigation & Tenant Switcher (45 seconds)
**On-screen:**
- Sidebar menu expanded
- Tenant switcher dropdown in header

**Voiceover:**
> "The main menu is on the left, organized into four categories: Monitoring, Configuration, Operations, and Tools. You can navigate by clicking on any page. If you work with multiple tenants, use the tenant switcher in the top-right. Click the dropdown, search for your tenant, and the UI instantly updates with that tenant's data."

**Actions:**
1. Click each category in sidebar to show sub-pages
2. Click tenant switcher dropdown
3. Type "tenant-abc" in search
4. Select "tenant-abc" → Dashboard refreshes with new data

**Visual Callouts:**
- Cursor highlights each menu category
- Zoom in on tenant switcher (20% zoom)
- Show spinner during tenant switch (1 second)

**Timestamp:** 1:30 - 2:15

---

### Segment 4: Creating an Agent (1 minute 15 seconds)
**On-screen:**
- Agent Management page at `/agents`
- Create Agent modal

**Voiceover:**
> "Let's create a new agent. Click on Configuration, then Agents. Here you see all your existing agents. Click the 'New Agent' button to open the form. Fill in the name, system prompt, and select an LLM provider. I'll name this 'Test Agent' and give it a simple prompt: 'You are a helpful assistant.' Select OpenAI GPT-4 as the provider. Click Save, and the agent appears in the list."

**Actions:**
1. Click "Configuration" → "Agents"
2. Click "+ New Agent" button
3. Type in form:
   - **Name:** "Test Agent"
   - **System Prompt:** "You are a helpful assistant that answers questions concisely."
   - **LLM Provider:** Select "OpenAI GPT-4" from dropdown
4. Click "Save"
5. Agent appears in table with status "Active"

**Visual Callouts:**
- Cursor highlights "+ New Agent" button
- Zoom in on form fields (15% zoom)
- Show success toast notification: "Agent created successfully"

**Timestamp:** 2:15 - 3:30

---

### Segment 5: Testing an Agent (1 minute)
**On-screen:**
- Agent Test page at `/agents/[id]/test`
- Test input/output panel

**Voiceover:**
> "Now let's test our new agent. Click on the agent row, then click the Test button. This opens the test sandbox. Enter a test input, like 'What is the capital of France?' and click Run Test. The agent processes the request in real-time, and you can see the output below. It correctly responds with 'Paris.' You can run multiple tests to verify the agent works as expected."

**Actions:**
1. Click on "Test Agent" row in table
2. Click "Test" button → Redirects to `/agents/[id]/test`
3. Type in input box: "What is the capital of France?"
4. Click "Run Test"
5. Show loading spinner (2 seconds)
6. Output appears: "The capital of France is Paris."

**Visual Callouts:**
- Cursor highlights "Test" button
- Zoom in on input box (20% zoom)
- Show streaming output (character-by-character animation)
- Highlight response time: "Response time: 1.2s"

**Timestamp:** 3:30 - 4:30

---

### Segment 6: Execution History & Wrap-Up (30 seconds)
**On-screen:**
- Execution History page at `/execution-history`
- Table with sortable columns, filters

**Voiceover:**
> "Finally, let's view the execution history. Click Operations, then Execution History. Here you can see all past executions, filter by status, date range, or agent, and export to CSV for reporting. That's it! You now know how to navigate the platform, create agents, test them, and view execution history. For more details, check out the Quick Start Guide or contact support. Thanks for watching!"

**Actions:**
1. Click "Operations" → "Execution History"
2. Show table with recent executions (including the test we just ran)
3. Click on "Status" filter → Select "Success"
4. Click on date range picker → Select "Last 7 days"
5. Hover over "Export CSV" button (don't click)

**Visual Callouts:**
- Cursor highlights the test execution row (highlight in green)
- Show filter dropdown animation
- Zoom out to show full table (10% zoom)

**Timestamp:** 4:30 - 5:00

---

## Recording Checklist

### Before Recording
- [ ] Clear browser cache and cookies
- [ ] Use a clean browser profile (no extensions)
- [ ] Prepare demo data in database (5-10 agents, 20+ executions)
- [ ] Test all actions in the script (dry run)
- [ ] Close unnecessary applications (reduce background noise)
- [ ] Use a quiet room with good lighting
- [ ] Check microphone levels (speak at normal volume)
- [ ] Have water nearby (avoid dry mouth)

### Loom Settings
- [ ] Recording type: **Screen + Camera**
- [ ] Camera position: **Bottom-right bubble**
- [ ] Resolution: **1080p (1920x1080)**
- [ ] Frame rate: **30fps**
- [ ] Auto-lighting: **Enabled**
- [ ] Noise filter: **Enabled**
- [ ] Live rewind: **Enabled** (in case of mistakes)

### During Recording
- [ ] Speak clearly and at a moderate pace
- [ ] Use cursor to highlight UI elements (circles, underlines)
- [ ] Pause between segments (makes editing easier)
- [ ] If you make a mistake, use "Live Rewind" to fix
- [ ] Avoid saying "um," "uh," "like" (use pauses instead)
- [ ] Smile when on camera (warm, welcoming tone)

### After Recording
- [ ] Review the video for errors
- [ ] Edit transcript (fix auto-generated errors)
- [ ] Add chapters (6 chapters for 6 segments):
  - 0:00 - Introduction
  - 0:30 - Dashboard Overview
  - 1:30 - Navigation & Tenant Switcher
  - 2:15 - Creating an Agent
  - 3:30 - Testing an Agent
  - 4:30 - Execution History & Wrap-Up
- [ ] Use AI to auto-generate title (Loom 2025 feature)
- [ ] Use AI to auto-generate summary (Loom 2025 feature)
- [ ] Enable comments (for user feedback)
- [ ] Set sharing permissions: **Anyone with the link**
- [ ] Copy Loom link and paste into this document (line 17)
- [ ] Verify file size < 50MB (if > 50MB, reduce quality to 720p)

---

## Post-Recording Tasks

### 1. Upload to Shared Drive
```bash
# Download video from Loom
# Upload to Google Drive / SharePoint / S3
# Share link in docs/video-walkthrough.md (this file)
```

### 2. Embed in Quick Start Guide
```markdown
<!-- In docs/quick-start-guide.md, add: -->
**Video Walkthrough:** [Watch 5-minute walkthrough](https://www.loom.com/share/your-video-id)
```

### 3. Share with Stakeholders
- Send link to operations team (email)
- Post in Slack #ai-agents-announcements
- Include in GA launch email (AC-8)

---

## Accessibility

### Closed Captions
- [ ] Enable auto-generated captions in Loom
- [ ] Review and edit captions for accuracy
- [ ] Export captions as `.srt` file (for manual uploads)

### Audio Description (Optional)
- [ ] Add audio description for visually impaired users (future enhancement)
- [ ] Describe visual elements verbally (e.g., "clicking the blue 'Save' button")

### Transcript
- [ ] Export full transcript from Loom
- [ ] Save as `docs/video-walkthrough-transcript.md`
- [ ] Link from this document

---

## Video Quality Checks

Before finalizing, verify:
- [ ] Audio is clear (no background noise, echo)
- [ ] Video is sharp (no blur, no pixelation)
- [ ] Cursor is visible and easy to follow
- [ ] All UI elements are readable (no small fonts)
- [ ] Transitions are smooth (no stuttering)
- [ ] Camera bubble is not blocking important UI (bottom-right is good)
- [ ] Duration is < 5:30 (5 minutes target, up to 30 seconds over is acceptable)
- [ ] File size is < 50MB (for fast loading)

---

## Alternative Formats

If Loom is unavailable, use these alternatives:

### Option 1: QuickTime (macOS)
```bash
# Record screen with QuickTime Player
# File → New Screen Recording
# Upload to YouTube (unlisted)
```

### Option 2: OBS Studio (Windows/Mac/Linux)
```bash
# Download OBS Studio (free, open-source)
# Set canvas to 1920x1080, 30fps
# Record to MP4 (H.264 codec)
# Upload to YouTube (unlisted)
```

### Option 3: Zoom
```bash
# Start a Zoom meeting (just yourself)
# Click "Share Screen"
# Record locally
# Export video, upload to Google Drive
```

---

**Generated by:** Bob (Scrum Master)
**Date:** January 2025
**Version:** 1.0

**Status:** 🎬 Ready to record

---

## Notes for Presenter

**Tone:**
- Professional but friendly
- Enthusiastic about the new UI (positive energy)
- Speak as if talking to a colleague, not reading a script

**Pacing:**
- Moderate speed (not too fast, not too slow)
- Pause after each action (1-2 seconds) to let viewers absorb
- Total word count: ~600 words for 5 minutes = 120 words/minute (natural pace)

**Cursor Movement:**
- Use smooth, deliberate cursor movements (no jerky motions)
- Circle important elements (e.g., circle the "Save" button)
- Underline text (e.g., underline the agent name in the table)
- Hover over UI elements to show tooltips (if applicable)

**Common Mistakes to Avoid:**
- ❌ Talking too fast (rushing through the script)
- ❌ Using jargon without explanation
- ❌ Not showing the full UI (zoomed in too much)
- ❌ Clicking too fast (viewers can't follow)
- ❌ Forgetting to mention keyboard shortcuts (Cmd+K, Cmd+D)

**Pro Tips:**
- ✅ Smile when on camera (viewers can hear the smile in your voice)
- ✅ Use hand gestures (if camera shows upper body)
- ✅ Take a deep breath before starting (reduces nervousness)
- ✅ Practice the script 2-3 times before recording
- ✅ Have the script visible (second monitor) but don't read it verbatim
