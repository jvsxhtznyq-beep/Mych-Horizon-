# 0001. Use SQLite through the standard library

- Date: 2026-03-10
- Status: Accepted

## Context
One small clinic, one server, a handful of staff. Bookings arrive at a low rate. The team wants no external services to operate.

## Decision
Store appointments in SQLite via Python's `sqlite3` module, on the application server.

## Consequences
- Easier: no database server to run; backups are file copies.
- Harder: one writer at a time; moving to several application servers would need a different store.
- Revisit if the clinic adds locations or a second application server.
