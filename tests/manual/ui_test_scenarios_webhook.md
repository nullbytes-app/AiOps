# Manual UI Test Scenarios - Webhook Features (Story 8.6)

**Test Date:** _____________
**Tester:** _____________
**Environment:** _____________

## Task 5: Payload Schema Validation UI

### Test Scenario 5.1: Schema Editor Visibility
- [ ] Create new agent with webhook enabled
- [ ] Verify "Payload Schema (Optional)" section appears in Triggers tab
- [ ] Verify section is hidden when webhook disabled

### Test Scenario 5.2: Example Schemas Dropdown
- [ ] Click "Load Example Schema" dropdown
- [ ] Verify 3 examples: ServiceDesk Plus Ticket, Jira Issue, Generic Event
- [ ] Select "ServiceDesk Plus Ticket"
- [ ] Verify JSON schema loads in text area with correct structure

### Test Scenario 5.3: JSON Schema Validation
- [ ] Enter valid JSON schema in text area
- [ ] Click "✓ Validate Schema" button
- [ ] Verify success message: "✅ Schema is valid (JSON Schema Draft 2020-12)"
- [ ] Enter invalid JSON (syntax error)
- [ ] Click "✓ Validate Schema" button
- [ ] Verify error message: "❌ Invalid JSON: ..."
- [ ] Enter valid JSON but invalid schema format
- [ ] Click "✓ Validate Schema" button
- [ ] Verify error message: "❌ Invalid JSON Schema: ..."

### Test Scenario 5.4: Schema Persistence
- [ ] Create agent with payload schema defined
- [ ] Save agent
- [ ] Reload agent detail view
- [ ] Verify payload schema persists (visible in webhook configuration)

---

## Task 6: Webhook Testing UI

### Test Scenario 6.1: Test Webhook Section Visibility
- [ ] Open agent detail view for active agent
- [ ] Scroll to webhook configuration section
- [ ] Click "🧪 Test Webhook" expander
- [ ] Verify section expands with sample payload text area

### Test Scenario 6.2: Send Valid Test Webhook
- [ ] Enter valid JSON payload matching agent's schema
- [ ] Click "🚀 Send Test Webhook" button
- [ ] Verify loading spinner appears
- [ ] Verify success message: "✅ Webhook accepted! (HTTP 202)"
- [ ] Verify execution ID displayed
- [ ] Verify caption: "Track execution status in agent execution history"

### Test Scenario 6.3: Send Invalid Test Webhook (Payload Validation)
- [ ] Enter invalid JSON payload (missing required fields)
- [ ] Click "🚀 Send Test Webhook" button
- [ ] Verify error message: "❌ Payload validation failed (HTTP 400)"
- [ ] Verify response details shown in JSON format

### Test Scenario 6.4: Send Test Webhook to Inactive Agent
- [ ] Create agent with status = "draft"
- [ ] Open agent detail view
- [ ] Click "🧪 Test Webhook" expander
- [ ] Enter valid payload
- [ ] Click "🚀 Send Test Webhook" button
- [ ] Verify warning message: "⚠️ Agent is not active (HTTP 403)"

### Test Scenario 6.5: Invalid JSON Payload (Syntax)
- [ ] Enter malformed JSON in test payload area
- [ ] Click "🚀 Send Test Webhook" button
- [ ] Verify error message: "❌ Invalid JSON payload: ..."

### Test Scenario 6.6: Full Response Details
- [ ] Send any test webhook
- [ ] After response displayed, click "Full Response Details" expander
- [ ] Verify full JSON response shown (status, execution_id, message)

---

## AC#3: Webhook URL Display

### Test Scenario AC3.1: Webhook URL Copy Button
- [ ] Create agent with webhook enabled
- [ ] Open agent detail view
- [ ] Locate "Webhook Configuration" section
- [ ] Verify webhook URL displayed in monospace code block
- [ ] Click "📋 Copy URL" button
- [ ] Paste into text editor
- [ ] Verify correct URL format: `http://localhost:8000/webhook/agents/{agent_id}/webhook`

---

## AC#4: HMAC Secret Show/Hide Toggle

### Test Scenario AC4.1: Default Masked State
- [ ] Open agent detail view
- [ ] Locate "HMAC Secret" field
- [ ] Verify secret is masked: `***********` (default state)
- [ ] Verify "👁️ Show" button visible
- [ ] Verify "📋 Copy" button disabled or hidden

### Test Scenario AC4.2: Show Secret
- [ ] Click "👁️ Show" button
- [ ] Verify loading spinner appears briefly
- [ ] Verify full base64-encoded secret displayed (44 characters)
- [ ] Verify button changes to "🙈 Hide"
- [ ] Verify "📋 Copy" button now enabled
- [ ] Verify security warning: "⚠️ Keep this secret secure..."

### Test Scenario AC4.3: Hide Secret
- [ ] With secret visible, click "🙈 Hide" button
- [ ] Verify secret returns to masked state
- [ ] Verify button changes back to "👁️ Show"

### Test Scenario AC4.4: Copy Secret
- [ ] Click "👁️ Show" to reveal secret
- [ ] Click "📋 Copy" button
- [ ] Paste into text editor
- [ ] Verify correct base64-encoded HMAC secret copied

---

## AC#5: Regenerate Secret

### Test Scenario AC5.1: Regenerate Confirmation Dialog
- [ ] Click "🔄 Regenerate Secret" button
- [ ] Verify confirmation dialog appears
- [ ] Verify warning message: "⚠️ **Are you sure?** This will invalidate all existing webhooks..."
- [ ] Verify "✅ Yes, Regenerate" and "❌ Cancel" buttons visible

### Test Scenario AC5.2: Cancel Regeneration
- [ ] Click "🔄 Regenerate Secret" button
- [ ] In confirmation dialog, click "❌ Cancel"
- [ ] Verify dialog closes
- [ ] Verify secret unchanged (no regeneration occurred)

### Test Scenario AC5.3: Confirm Regeneration
- [ ] Note current secret (show and copy)
- [ ] Click "🔄 Regenerate Secret" button
- [ ] In confirmation dialog, click "✅ Yes, Regenerate"
- [ ] Verify loading spinner appears
- [ ] Verify success message: "✅ New HMAC secret generated. Old webhooks will no longer work."
- [ ] Click "👁️ Show" to reveal new secret
- [ ] Verify new secret is different from old secret

---

## Edge Cases & Error Handling

### Test Scenario E1: Network Error Handling
- [ ] Stop API server (simulate network error)
- [ ] Try to send test webhook
- [ ] Verify error message: "❌ Failed to send test webhook (network error)"

### Test Scenario E2: Large Payload
- [ ] Enter very large JSON payload (10KB+)
- [ ] Send test webhook
- [ ] Verify request completes without timeout

### Test Scenario E3: Special Characters in Payload
- [ ] Enter payload with special characters: `{"test": "value with \"quotes\" and \n newlines"}`
- [ ] Send test webhook
- [ ] Verify payload handled correctly

---

## Cross-Browser Testing (Optional)

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)

---

## Accessibility Testing (Optional)

- [ ] Tab navigation works through all form fields
- [ ] Screen reader announces button states (Show/Hide)
- [ ] Color contrast meets WCAG AA standards
- [ ] Keyboard shortcuts work (Enter to submit forms)

---

## Test Summary

**Total Scenarios:** 25+
**Passed:** _____
**Failed:** _____
**Blocked:** _____
**Pass Rate:** _____%

**Issues Found:**
1. _____________________________________
2. _____________________________________
3. _____________________________________

**Notes:**
_________________________________________________
_________________________________________________
