# Architecture proposal: appointment reminders by email and SMS

Date: 2026-11-01 | Status: proposed | Decision record: [0003](../decisions/0003-reminders-via-outbox-table-and-timer.md)

## 1. Problem definition
Patients should get a reminder before each appointment by email, and by SMS where they gave a number. The hard parts are sending each reminder exactly once despite crashes and retries, and never reminding about cancelled appointments.

## 2. Requirements
- Functional: reminders 24 hours and 2 hours before an appointment; no reminder for cancelled appointments; email always, SMS when a number and consent exist.
- Non-functional (estimates, labeled assumptions): at most about 200 appointments a week, so about 400 reminders a week; a reminder may be up to 10 minutes late; no duplicates.
- Constraints: one server and SQLite (decision 0001); standard library only (CLAUDE.md); SMS costs money (approval point).

## 3. Proposed architecture
A `reminders` table in the existing SQLite database acts as an outbox. Booking inserts two pending reminders in the same transaction as the appointment; cancelling marks them cancelled. A systemd timer runs `python3 -m booking.reminders send-due` every 5 minutes; it claims due reminders, sends them through a channel adapter (email by `smtplib`, SMS by the provider's HTTPS API through `urllib`), and records the result.

## 4. Component responsibilities
| Component | Responsibility | Owns data |
|---|---|---|
| `Scheduler` (existing) | Creates and cancels reminders with appointments | `appointments`, `reminders` rows it writes |
| `reminders.send_due()` | Claims due rows, sends, records outcome, schedules retries | `reminders.status`, `attempts`, `last_error` |
| `EmailChannel`, `SmsChannel` | Deliver one message; raise on failure | None |
| systemd timer | Runs the sender every 5 minutes | None |

## 5. Communication and data flow
Book: one transaction writes the appointment and two reminders (`pending`, `send_at`). Timer run: `UPDATE ... SET status='sending', claimed_at=now WHERE status='pending' AND send_at <= now` claims rows, then each row is sent and marked `sent` or returned to `pending` with backoff. Rows stuck in `sending` for 15 minutes are reclaimed. A reminder whose appointment has already started is marked `expired`, not sent.

## 6. Dependencies
| Dependency | Failure impact | Alternative |
|---|---|---|
| Clinic SMTP server | Email reminders delayed | Retry; transactional email provider later |
| SMS provider (to be chosen) | SMS delayed | Retry; email still goes out |

## 7. Failure scenarios
| Component | Failure | Effect | Detection | Mitigation |
|---|---|---|---|---|
| SMS or SMTP provider | Down or slow | Reminder not sent | `attempts` growing; daily failure count | 10 s timeout, exponential backoff, give up after 5 attempts and mark `failed` |
| Sender process | Crashes mid-run | Rows stuck in `sending` | Rows in `sending` older than 15 minutes | Reclaim stuck rows; the claim makes a resend possible, so messages carry an idempotency key where the provider supports it |
| Timer or server | Down for hours | Missed reminders | Health check on the last run time | On restart, send only reminders still before the appointment; mark the rest `expired` |
| Two overlapping runs | Duplicate sends | Patient gets two messages | Duplicate check in tests | Claim by conditional `UPDATE` in one transaction; SQLite allows one writer |
| Cancellation after claim | Reminder for a cancelled visit | Confusion | Test | Re-check the appointment status right before sending |

## 8. Security considerations
Provider keys come from the environment or a secret store, never the repository. Messages carry only the date, time and clinic name, no clinical details. Logs omit phone numbers and email addresses. Patient consent for SMS and email must be recorded before sending; the applicable rules need the owner's confirmation.

## 9. Performance considerations
About 400 reminders a week is trivial for SQLite and a 5-minute timer. Add an index on `(status, send_at)`.

## 10. Alternatives considered
| Alternative | Why not chosen |
|---|---|
| Message broker and worker service (for example a queue plus workers) | Violates proportionality: adds infrastructure for about 400 messages a week, and conflicts with decision 0001 |
| Background thread inside the web process | Reminders lost on restart; no retry state |
| External reminder SaaS | Recurring cost and patient data shared with a third party; possible later |

## 11. Trade-offs
Simple and reliable at this scale, and up to 5 minutes late by design. Revisit if the clinic adds servers (decision 0001's trigger) or volume grows a hundredfold.

## 12. Implementation strategy
1. Migration adding `reminders` (expand only; no change to existing tables).
2. Create and cancel reminders in `Scheduler` with tests.
3. `send_due()` with an email channel and a fake SMS channel in tests; overlap, retry and expiry tests.
4. Approval point: choosing and paying for an SMS provider, and storing its key.
5. Deploy (gated), enable the timer, watch the first day's sent and failed counts.
