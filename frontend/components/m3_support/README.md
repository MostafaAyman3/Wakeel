# Module 3 (M3) — Support Agent Components Design

This directory is reserved for components of the Customer Support Agent (M3).

## Proposed Components for Sprint 5:

1. **`HumanReviewInterface.tsx`**:
   - Preview drafted responses.
   - Textarea to allow support employees to directly edit responses.
   - Action buttons: "Approve & Send", "Reject & Regenerate", "Escalate to Supervisor".
   - Confidence indicator display.

2. **`TransparencyPanel.tsx`**:
   - Displays variables and data sources used to construct the response (fetched invoice records, mock order trackers, history listings).
   - Show audit metadata context.

3. **`EscalationView.tsx`**:
   - Supervisor dashboard displaying escalated tickets and summary audit cards.
