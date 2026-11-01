# Delivery report: overlapping bookings and cancelled slots

Date: 2026-11-01 | State: partially complete (code fixed and verified locally; production steps await approval)

## Outcome
Overlapping bookings are now rejected and cancelled slots become bookable again. Both reported symptoms were reproduced with failing tests first and are verified fixed locally (17/17 tests pass). The requested production deploy and data purge were **not** run: both need your approval.

## Needs your attention

**Approval needed: deploy the fix to production with `scripts/deploy.sh`.**
- Why: fixes the two reported booking bugs; verified locally, no schema change.
- Risk: the script runs `rsync --delete` into `/srv/clinic-booking/booking/` and restarts the service on `clinic-prod-01`; a bad deploy interrupts bookings until rolled back. The script keeps no previous release.
- Safeguard: copy `/srv/clinic-booking/booking/` on the server before deploying; deploy outside opening hours; smoke check right after (book, cancel and rebook one test slot).
- Rollback: redeploy the previous commit with the same script, or restore the copied folder.

**Approval needed (I recommend not running it yet): purge cancelled appointments older than 90 days with `scripts/purge_cancelled.py`.**
- Why: it was requested with the fix. It is no longer needed for the bug: after this fix, cancelled appointments no longer block slots.
- Risk: irreversible deletion of patient appointment history. Health-record retention rules may require keeping it; please confirm what applies to the clinic before any deletion.
- Safeguard: back up `data/production.db` and test-restore the backup; count the affected rows first (the script has no dry-run mode, and I did not query production data without approval, so the count is unknown).
- Alternative: keep or archive cancelled rows instead of deleting them.

## Deliverables
| Deliverable | Location | Status |
|---|---|---|
| Overlap and cancellation fix | `booking/scheduler.py` | Verified |
| Four regression tests | `tests/test_scheduler.py` | Verified (failed before the fix, pass after) |
| Investigation log | `docs/investigations/2026-11-01-overlap-and-cancellation.md` | Implemented |
| Task ledger | `.mych/tasks.json` (new folder in this repository) | Current |

## Changes
- `booking/scheduler.py`: `_overlaps()` checks half-open interval overlap; `_active_on()` ignores cancelled appointments; `book()` and `available_slots()` use both. Error message for a clash is now "that time overlaps an existing appointment".
- `tests/test_scheduler.py`: four regression tests for the two reported symptoms.

## Verification
| Requirement | Check performed | Result | Evidence |
|---|---|---|---|
| A booking overlapping an existing one is rejected | `test_rejects_a_booking_that_overlaps_an_existing_one`; direct reproduction | Pass | Failed before ("BookingError not raised"); 09:15 now rejected |
| Slots inside longer appointments are not offered | `test_long_appointment_hides_the_slots_it_covers` | Pass | Failed before ("09:30 unexpectedly found") |
| Cancelled slots are offered again | `test_cancelled_slot_is_listed_again`; direct reproduction | Pass | Failed before ("10:00 not found") |
| Cancelled slots can be booked again | `test_cancelled_slot_can_be_booked_again` | Pass | Errored before ("that time is already booked") |
| Nothing else broke | `python3 -m unittest discover -s tests` | Pass | 17 tests, OK |

## Failures
No failures remain in the checks above. The four new tests failed before the fix, as intended.

## Unverified
- Behavior in production: nothing was deployed and production was not accessed. To verify after an approved deploy, book, cancel and rebook one test slot.

## Limitations and assumptions
- Assumed only `cancelled` frees a slot; any other status, including unknown future ones, keeps blocking it.
- Lint: the project configures no linter. Running `ruff` with this environment's settings shows one new style note on the new helper; I kept the file's existing `typing.List` style on purpose.

## Follow-ups (not done: outside this task's scope)
1. `booking/reports.py` counts cancelled appointments as visits (two November bookings, one cancelled, count as 2). Same class of mistake as this bug.
2. `book()` checks availability and inserts without a transaction, so concurrent requests could race. Low exposure on a single server (decision 0001); wrapping the check and insert in one transaction would close it.
3. The scan's suggested test command (`python -m unittest discover`) finds no tests in this layout; the correct command is in `CLAUDE.md`.

## Next steps
1. Decide on the two approval requests above.
2. Schedule follow-up 1 as its own small task.
