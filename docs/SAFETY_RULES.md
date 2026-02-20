# Safety Rules and Escalation Flow

## Overview

This document defines the safety rules and escalation procedures for the Elevana Hackathon application.

## Safety Rules

### Content Moderation Rules

**Status:** Defined for MVP (policy-level, implementation pending)

#### Categories to Monitor
- [x] Harmful content (e.g. threats, self-harm, glorification of harm)
- [x] Hate speech (targeting protected classes)
- [x] Violence (graphic or non-graphic)
- [x] Self-harm (ideation, intent, instructions)
- [x] Illegal activities (planning, instructions, admission of serious crime)
- [x] Personal information requests (doxxing, sensitive data disclosure)
- [x] Spam/abuse (harassment, scams, repetitive unwanted content)

#### Rule Implementation (MVP policy)
- Rules will be checked in `backend/services/agent.py`
- Each message will be evaluated before processing and response generation
- Rules can be configured via settings or database
- Each violation is mapped to a severity level (`low`, `medium`, `high`, `critical`)
- High/critical violations will trigger escalation according to the flow below

### Safety Check Response

```python
{
    "safe": bool,        # Whether content passes safety checks
    "reason": str,       # Reason for rejection (if unsafe)
    "escalate": bool,    # Whether to escalate to human review
    "severity": str      # low/medium/high/critical
}
```

## Escalation Flow

### Triggers

Escalation should occur when:
1. Content fails safety checks with high severity
2. User requests human assistance
3. System detects potential harm
4. Multiple safety violations in short time
5. User expresses distress or crisis indicators

### Escalation Levels

#### Level 1: Automatic Filtering
- **Action:** Block unsafe content, return generic message
- **Response:** "I can't help with that. How else can I assist you?"
- **Logging:** Log incident for review

#### Level 2: Flagged Review
- **Action:** Flag conversation for human review
- **Response:** Continue conversation but flag for review
- **Notification:** Alert moderation team

#### Level 3: Immediate Escalation
- **Action:** Pause conversation, notify human moderator
- **Response:** "Let me connect you with a team member who can better assist."
- **Priority:** High priority queue

#### Level 4: Emergency Escalation
- **Action:** Immediate human intervention
- **Response:** Direct to crisis resources if applicable
- **Priority:** Critical

### Escalation Flow Diagram

```
User Message
    ↓
Safety Check
    ↓
┌─────────────────┐
│ Is Safe?        │
└─────────────────┘
    ↓ Yes          ↓ No
Process          ┌─────────────────┐
    ↓            │ Check Severity  │
Response         └─────────────────┘
                      ↓
            ┌─────────┴─────────┐
            ↓                   ↓
        Low/Medium          High/Critical
            ↓                   ↓
        Level 1            Level 3/4
        Filter             Escalate
```

## Implementation Status

### Current State
- [x] Safety rule structure defined
- [x] Escalation flow documented
- [x] MVP safety policy defined (this document)
- [ ] Safety rules implemented in code
- [ ] Escalation system implemented
- [ ] Human review queue system
- [ ] Crisis resource integration

### Next Steps
1. Implement safety checking service based on this MVP policy
2. Wire escalation decisions into logging/alerting and UI
3. Build moderation dashboard (optional)
4. Integrate crisis resources if needed and appropriate

## Configuration

Safety rules can be configured via:
- Environment variables
- Database configuration table
- Admin panel (future)

## Monitoring

- Track safety violations
- Monitor escalation rates
- Review false positives
- Update rules based on patterns

## Notes

- Safety rules should be tailored to the specific use case
- Escalation flow may need adjustment based on deployment context
- Consider legal and compliance requirements
- Regular review and updates of safety rules recommended
