# Invention: reducing no-shows without paid SMS

Date: 2026-11-01 | Stage: prototype planned, awaiting authorization (not built)

## Frame
- Job: the clinic wants fewer slots wasted by no-shows without paying per message.
- Hard part: SMS reminders work but cost money per message; email is free but read less; cancelling takes patients effort, so many simply don't come.
- Assumptions existing solutions share: (a) the clinic must push a reminder; (b) a no-show is a memory problem; (c) a no-show's slot is lost.
- Why now: cancelled slots now become bookable again (booking fix e109f3b), so released slots can be refilled; an email reminder pipeline is proposed (decision 0003).

## Prior art (search results used as leads; the primary papers were not opened in this session)
| Approach | Where it falls short | Evidence |
|---|---|---|
| SMS reminders | Effective but modest; costs money per message | Rapid review (Oikonomidi et al., JAMIA 2023) reported high-certainty, median risk ratio about 0.91 (lead) |
| Phone calls and patient navigators | Staff time | Same review: moderate certainty (lead) |
| Predictive overbooking | Effect uncertain; risk of crowding | Same review: uncertain (lead); one endoscopy simulation favorable (lead) |
| Financial incentives, contracts | Mixed results by setting | Search lead, PMC9933067 |
| Waitlist backfilling, confirm-or-release | Not covered by the results found | Gap: needs a targeted search |

## Concepts (distinct mechanisms)
### C1. Patient-owned reminders
- Mechanism: the confirmation email carries a calendar event with alarms 24 hours and 2 hours before; the patient's own phone reminds them, at no cost to the clinic.
- What is new: nothing fundamental; common practice elsewhere, new to this clinic.
- Feasibility: **Currently feasible** (a standard calendar file attached to the email).
- Riskiest assumption: at least half of patients add the event. Time to signal: about 2 weeks.

### C2. Confirm-or-release with waitlist backfill
- Mechanism: 48 hours before, an email offers one-click "Keep" or "Release"; released or unconfirmed slots are offered by email to a waitlist of patients who want an earlier slot. It removes the effort of cancelling and refills the slot, instead of only reminding.
- What is new: the combination for this clinic; the search found no evidence either way on waitlist backfilling.
- Feasibility: **Currently feasible**, on top of the reminders outbox (decision 0003) plus a waitlist table.
- Riskiest assumption: waitlisted patients accept short-notice slots often enough (at least 30% of released slots refilled). Time to signal: about 4 weeks.

### C3. Risk-aware double booking
- Mechanism: predict each booking's no-show risk from the clinic's history (lead time, time of day, earlier no-shows) and allow one extra patient on high-risk slots (borrowed from airline overbooking).
- What is new: little; studied in healthcare with uncertain results.
- Feasibility: **Feasible with substantial engineering**: needs labeled history, a model, and an overflow plan.
- Riskiest assumption: the history predicts no-shows well enough; testing it means reading production data, which needs approval. Time to signal: about 8 weeks.

### C4. Booking-time commitment cue
- Mechanism: when booking, the patient picks their own reminder time and writes one line about how they will get there (an "implementation intention" prompt).
- What is new: applying a behavioral technique at booking time rather than at reminder time.
- Feasibility: **Experimental**: technically trivial, but the effect is unproven at this clinic's scale and hard to detect with small numbers.
- Riskiest assumption: a measurable effect with a few hundred bookings. Time to signal: 8 weeks or more.

## Comparison
| Concept | Value | Feasibility | Novelty | Resources | Risk | Time to signal |
|---|---|---|---|---|---|---|
| C1 | Low to medium | Currently feasible | Low | Hours | Low | 2 weeks |
| C2 | Medium to high: recovers capacity | Currently feasible | Medium (combination) | Days, after the reminders outbox | Patient response | 4 weeks |
| C3 | Medium | Substantial engineering | Low | Weeks plus data access | Crowding; data access | 8 weeks |
| C4 | Unknown | Experimental | Medium | Hours | Undetectable effect | 8 weeks or more |

## Chosen direction
C2, chosen by this session under the workflow's rule (best value to time-to-signal while the owner cannot be asked). C1's calendar file costs little and can ride along in C2's emails. The owner should confirm.

## Prototype plan (stopped here: prototyping not authorized)
- Assumption under test: released slots are refilled from the waitlist often enough.
- Experiment: a 4-week pilot on one clinician's schedule: keep-or-release emails 48 hours ahead and a short-notice waitlist; compare against the previous 8 weeks.
- Success criteria (set before building): at least 30% of released slots refilled, and no-shows down by at least 25% relative to baseline.
- Kill criteria: under 10% refilled after 4 weeks, or more than two patient complaints about the emails.
- Approval points: emailing patients for a new purpose (consent); reading historical production appointments for the baseline; changing front-desk routines.
- Authorization: awaiting the owner.
