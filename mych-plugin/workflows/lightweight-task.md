# Lightweight Task Workflow

The fast path for Tier 1 work: a small, clear change in one component, low risk and easy to revert. The goal is a correct change and an honest check with no ceremony.

## When it applies

All of these hold:

- The intent is clear, and so is roughly where the change goes.
- One component, function, file or page is affected (a rename across files counts if it is mechanical).
- A mistake is easy to notice and to revert.
- No security, data deletion, money or production exposure.

Examples: fix an off-by-one error with a known location; add a field to a form that follows existing patterns; update a dependency patch version with no breaking changes; adjust copy; write a small utility function with tests.

## The loop

1. **Understand.** Restate the change to yourself in one sentence, with its observable result.
2. **Locate.** Find the exact code and read it with its immediate callers and existing tests. Check the working tree for uncommitted work you must not disturb.
3. **Change.** Make the smallest change that achieves the result, in the file's existing style. Add or adjust a test when behavior changes and the project has tests.
4. **Check.** Run the most relevant fast check: the affected test file, the type checker, the linter, or the command itself. If nothing can be run, do a careful static review and say so.
5. **Report.** In two to five lines: what changed (files), how it was checked (command and result), and anything unverified.

## Escalate when

Switch to the standard lifecycle ([execution-lifecycle.md](execution-lifecycle.md)) and say so in one line if any of these happen:

- The change touches more components than expected, or a public interface.
- The cause of a bug is not where it appeared to be ([debugging.md](debugging.md)).
- An unrelated test fails, or the check fails for a reason you do not understand.
- The change turns out to involve security, data, money or production ([sensitive-change.md](sensitive-change.md)).
- Requirements conflict, or the intended behavior is ambiguous in a way that matters ([clarification-protocol.md](../core/clarification-protocol.md)).

## Keep it light

- No written plan, task list, decision record or design specification.
- One discipline (usually the Engineer). No role-play.
- No questions about conventions the code already shows.
- No unrelated refactoring. Mention worthwhile improvements in one line instead.

## Report example

```text
Fixed the pagination off-by-one in api/orders.py (page offset used page instead of page - 1).
Added test_second_page_starts_after_first_page in tests/test_orders.py.
Ran: pytest tests/test_orders.py  ->  14 passed.
Not checked: the admin export, which uses its own pagination helper.
```
