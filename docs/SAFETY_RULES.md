# Safety Rules and Escalation Flow

## Overview

This document defines the safety rules and escalation procedures for the AI Niru Hackathon application.

## Safety Rules

### Content Moderation Rules

**Status:** To be defined based on use case

#### Categories to Monitor
- [ ] Harmful content
- [ ] Hate speech
- [ ] Violence
- [ ] Self-harm
- [ ] Illegal activities
- [ ] Personal information requests
- [ ] Spam/abuse

#### Rule Implementation
- Rules will be checked in `backend/services/agent.py`
- Each message will be evaluated before processing
- Rules can be configured via settings or database

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
- [ ] Safety rules implemented
- [ ] Escalation system implemented
- [ ] Human review queue system
- [ ] Crisis resource integration

### Next Steps
1. Define specific safety rules based on use case
2. Implement safety checking service
3. Build escalation system
4. Create moderation dashboard (optional)
5. Integrate crisis resources if needed

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
