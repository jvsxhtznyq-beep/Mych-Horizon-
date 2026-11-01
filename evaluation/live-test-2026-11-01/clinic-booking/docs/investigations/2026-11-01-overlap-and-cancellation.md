# Investigation: overlapping bookings and cancelled slots

Started: 2026-11-01 | Status: fixed, verified locally

## Symptom
- Expected: a booking that overlaps an existing appointment is rejected; a cancelled slot becomes bookable again.
- Actual (reported): a patient was booked at 09:15 while 09:00-09:30 was taken; cancelled slots never free up.
- Frequency: deterministic for the inputs below.

## Environment and conditions
Local checkout of clinic-booking at 0a00105, Python 3.13.18, in-memory SQLite. Production was not accessed.

## Reproduction
`python3 -m unittest tests.test_scheduler` with four new tests, before any fix: FAILED (failures=3, errors=1).

## Hypotheses
| ID | Hypothesis | Test | Result | Status |
|---|---|---|---|---|
| H1 | `book()` compares start times for equality instead of interval overlap | Overlap test; read `scheduler.py:41` | Test fails with "BookingError not raised"; code is `existing.start == start` | Confirmed |
| H2 | Cancelled appointments still count as occupying their slot | Read `scheduler.py:23,40`; E2 | Neither check filters `status` | Confirmed |
| H3 | 09:15 is altered in the SQLite round trip, so comparisons miss | E1: store 09:15, read it back | Read back equal to the original | Refuted |
| H4 | `cancel()` does not persist the status | E2: cancel, then `store.get()` | Status is `cancelled` | Refuted |

## Root cause
Availability was decided by exact start-time equality and ignored appointment status. The trigger was a booking at a non-slot-aligned time (09:15) and, separately, any cancellation.

## Fix
`booking/scheduler.py`: `_overlaps()` for half-open interval overlap, `_active_on()` to ignore cancelled appointments; both used by `book()` and `available_slots()`.

## Verification
`python3 -m unittest discover -s tests`: 17 passed. Direct reproduction: 09:15 rejected; cancelled 10:00 listed again.

## Residual risks and follow-ups
- `booking/reports.py` `monthly_visit_count()` also ignores status: one of two November visits cancelled still counts as 2. Same class of mistake, outside this task's scope; not changed.
- `book()` checks and then inserts without a transaction; two concurrent requests could still race. Not reproduced; exposure is limited by the single-server design (decision 0001).
