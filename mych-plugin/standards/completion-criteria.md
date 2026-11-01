# Completion Criteria

When a deliverable may be called complete, when it may be called verified, and how to label anything in between. Code generation is not delivery; a deliverable that was never exercised is not done.

## Definition of done

A deliverable is complete only when all of these hold:

1. The agreed requirements are addressed.
2. The required files or artifacts exist.
3. Important functionality has been checked.
4. Relevant tests have been performed.
5. Known limitations are documented.
6. The output is accessible to the owner: a path, link or artifact they can open.

## Status vocabulary

For tasks:

| Status | Meaning |
|---|---|
| Not started | No work done |
| In progress | Work underway |
| Blocked | Cannot proceed; the blocker and what would unblock it are recorded |
| Completed | The work exists and meets its expected result as far as the author can tell |
| Verified | The task's verification method was executed and the evidence is recorded |

For deliverables in reports: *implemented* (exists), *tested* (checks ran, with results), *verified* (requirement traced to executed evidence), *unverified* (not yet checked, with the reason).

**Completed is not verified.** "The endpoint is written" is completed. "The endpoint returns 201 with the created record and 422 for invalid input, as shown by the two integration tests that ran" is verified.

## Complete and verified by deliverable type

| Deliverable | Complete when | Verified when |
|---|---|---|
| Code change | The change is made and builds | Relevant tests ran and passed; behavior observed |
| Bug fix | The cause is fixed | A regression test failed before and passes after; the reproduction passes |
| Feature | All acceptance criteria are implemented | Each criterion is traced to an executed test or a demonstrated task |
| User interface | Screens and states are built | Top tasks walked; accessibility checklist run; responsive widths checked |
| Design specification | Tokens, components, states and screens are specified | Reviewed against the design quality bar; contrast computed |
| Research report | The question is answered with sources | Every important claim checked against a source opened in this session |
| Architecture proposal | All required sections are filled in proportion | Each requirement and failure scenario walked through the design |
| Invention concept | Concepts are evaluated with feasibility ratings | Novelty claims checked against mapped prior art |
| Prototype | It runs | It ran against pre-set criteria; results recorded with conditions |
| Documentation | Written | Instructions followed as written, and they worked |
| Deployment or release | The artifact is built and the procedure is ready | Executed with approval; health checks observed; rollback path confirmed |

## Partial delivery

When not everything is done, deliver what is solid and label the rest:

- Lead the report with the overall state: complete, partially complete, or blocked.
- List finished items as *verified*, *tested* or *implemented*, each with its evidence.
- List unfinished items with the reason and the next step.
- Never present a stub, mockup or placeholder as a working feature.

## Before claiming completion

- [ ] Every requirement has a status and, where verified, evidence.
- [ ] Every check reported as passing actually ran in this session.
- [ ] Failures and skipped checks are reported with reasons.
- [ ] Limitations and assumptions are listed.
- [ ] The owner can reach every deliverable.
