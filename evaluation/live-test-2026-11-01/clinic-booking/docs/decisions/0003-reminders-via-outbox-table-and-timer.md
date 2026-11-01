# 0003. Send reminders from an outbox table drained by a timer

- Date: 2026-11-01
- Status: Proposed
- Deciders: owner to accept; proposal by the implementation session

## Context
Reminders by email and SMS are requested. The system runs on one server with SQLite (decision 0001) and allows only the standard library. Volume is about 400 reminders a week.

## Problem
How should reminders be scheduled and sent so each goes out once, on time, and never for a cancelled appointment?

## Options
1. **Outbox table in SQLite plus a 5-minute systemd timer.** Pros: no new infrastructure, transactional with bookings, survives restarts. Cons: up to 5 minutes late.
2. **Message broker with a worker service.** Pros: scales far beyond need. Cons: new infrastructure to run; disproportionate.
3. **Background thread in the web process.** Pros: simplest code. Cons: lost on restart, no retry state.
4. **External reminder service.** Pros: no code. Cons: cost, patient data shared with a third party.

## Decision
Option 1, as specified in the [architecture proposal](../architecture/2026-11-01-appointment-reminders.md).

## Consequences
- Easier: reminders are created and cancelled in the same transaction as appointments.
- Harder: the sender must claim rows carefully and reclaim stuck ones.
- Approval needed before rollout: SMS provider choice and cost; patient consent rules.

## Alternatives rejected
- Broker and workers: no requirement fails without them at this scale.
- Background thread: loses reminders on restart.
- External service: cost and data sharing, with no requirement that justifies them yet.
