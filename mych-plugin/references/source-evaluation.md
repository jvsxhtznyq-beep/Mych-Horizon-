# Source Evaluation

How to judge sources, check that they apply to the versions in use, scrutinize benchmarks, resolve contradictions and cite honestly. Used by the Researcher ([researcher.md](../modes/researcher.md)) and by anyone making a factual claim.

## Contents

- [Source tiers](#source-tiers)
- [Credibility signals and red flags](#credibility-signals-and-red-flags)
- [Version and date checks](#version-and-date-checks)
- [Benchmark scrutiny](#benchmark-scrutiny)
- [Resolving contradictions](#resolving-contradictions)
- [Citation format](#citation-format)
- [Where authoritative information usually lives](#where-authoritative-information-usually-lives)

## Source tiers

| Tier | Source type | Use as |
|---|---|---|
| 1 | Official documentation, specifications and standards (RFCs, W3C and WHATWG specifications, language references) | Primary evidence |
| 1 | Source code, changelogs, release notes, migration guides, maintainers' statements in official channels | Primary evidence, especially for version-specific behavior |
| 2 | Peer-reviewed research; benchmarks with published, reproducible methods | Strong evidence within their stated conditions |
| 2 | Your own reproducible experiment, with environment and method recorded | Strong evidence for your conditions |
| 3 | Reputable independent technical writing (engineering blogs of credible organizations, books by recognized practitioners) | Supporting evidence; check dates |
| 4 | Community answers, forum posts, tutorials, issue comments by non-maintainers | Leads to verify, not conclusions |
| 5 | Marketing pages, vendor comparisons, undated or anonymous content, content farms | Claims to verify, never evidence on their own |

A lower-tier source can be right and a higher-tier one outdated. Tiers set the burden of proof, not the truth.

## Credibility signals and red flags

Signals of credibility: named author with relevant expertise; publication and update dates; versions stated; methods and data shared; limitations acknowledged; consistency with primary sources; corrections published when wrong.

Red flags:

- No date, no version, no author.
- Claims without methods ("10x faster") or with cherry-picked conditions.
- A vendor comparing itself with competitors.
- Text that reads as generated filler: generic, repetitive, confidently vague, with citations that do not support the claim.
- Code examples that use APIs absent from the documented version.
- Many sites repeating the same claim with no primary source behind it.

## Version and date checks

1. Determine the version in use from the project (lockfiles, manifests, `--version` output) before researching behavior.
2. Read the documentation for that version, not the latest by default; most documentation sites offer version selectors.
3. Read changelogs between the version in use and the version a source describes when they differ.
4. Record "as of version X, documentation updated DATE" next to version-sensitive claims.
5. Treat anything older than a few major versions of a fast-moving tool as suspect until confirmed.

## Benchmark scrutiny

Before relying on any benchmark, answer:

| Question | Why it matters |
|---|---|
| Is the workload realistic for our use? | Micro-benchmarks rarely predict application performance |
| What hardware, operating system and runtime versions? | Results do not transfer across environments |
| What configuration and tuning for each contender? | Default settings against tuned settings is not a fair comparison |
| Were there warm-up runs, and how many repetitions? | Cold starts and JIT compilation distort single runs |
| Is variance reported (spread, confidence intervals)? | Differences inside the noise are not differences |
| Can it be reproduced from published code and data? | Unreproducible results are anecdotes |
| Who ran it, and who funded it? | Incentives shape choices of workload and configuration |
| How old is it, relative to the versions compared? | Performance changes between releases |

When the decision depends on performance, run a small benchmark on your own workload when tools allow, and report results with their conditions.

## Resolving contradictions

1. Check that both sources discuss the same version, configuration and conditions.
2. Prefer the primary source; read the code or the specification if needed.
3. Check whether one source has been corrected or superseded.
4. Run an experiment when the question is testable and tools allow.
5. If still unresolved, report both positions, the evidence for each, and what would settle it. Never average contradictory claims into a false consensus.

## Citation format

- Cite only sources opened in this session; never cite from memory as if verified.
- Format: Title, publisher or author, version if applicable, date published or updated, link, date accessed.
- Quote exactly when the wording matters, and keep quotes short.
- Point to the most specific location possible (section anchor, line in a changelog).
- Never invent a citation, quote, statistic, version number or benchmark result. If you cannot find support for a claim, label it as inference, hypothesis or unknown.

## Where authoritative information usually lives

| Topic | Look first at |
|---|---|
| A language's behavior | The official language reference and standard library documentation; language enhancement proposals (for example PEPs, TC39 proposals) |
| A library or framework | Its official documentation for the version in use, its changelog and release notes, its source repository |
| Web platform features | Web standards specifications and well-maintained reference documentation such as MDN; browser compatibility data |
| Network protocols | IETF RFCs |
| Security advisories | CVE records, the National Vulnerability Database, GitHub Security Advisories, the vendor's security bulletins |
| Secure development practice | OWASP projects (Top 10, Application Security Verification Standard, cheat sheets) |
| Accessibility | W3C Web Accessibility Initiative: WCAG and its Understanding documents |
| Cloud services | The provider's official documentation, service limits pages and pricing pages |
| Package metadata | The package registry entry and the linked repository |
