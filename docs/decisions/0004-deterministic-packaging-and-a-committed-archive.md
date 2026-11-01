# 0004. Build deterministic archives and commit the release ZIP

- Date: 2026-11-01
- Status: Accepted
- Deciders: implementation session; the owner may revisit

## Context

The specification asks for a ZIP suitable for Claude's skill upload, an operational packager that verifies the archive, and the location of the generated ZIP in the final report. Claude's upload documentation requires the archive to contain the skill folder as its top level. The build ran in an ephemeral cloud container, so a ZIP left only in the container would be lost; the owner needs it in the repository or as a downloaded file.

## Problem

How should archives be built so they can be trusted and reproduced, and where should the release ZIP live?

## Options

1. **Deterministic build, release ZIP committed under `dist/`, with a test that fails when the committed archive no longer matches the source.**
2. **Build on demand only; never commit archives.**
3. **Publish archives as GitHub releases.**

## Decision

Option 1. `package-skill.py` sorts entries, fixes timestamps (1980-01-01, or `SOURCE_DATE_EPOCH` when set), normalizes permissions (scripts 0755, other files 0644), keeps `mych-plugin/` as the single top-level folder, excludes development artifacts and secret-like files, then reopens the archive and verifies structure, frontmatter, CRCs and byte-for-byte content against the source. `dist/mych-plugin-<version>.zip` is committed. `tests/test_dist_archive.py` fails if the committed archive's contents drift from the skill folder.

## Reasoning

Determinism makes the committed archive reproducible and reviewable: rebuilding unchanged sources gives the same contents. Committing it gives the owner a download path that survives the container. The staleness test prevents shipping an outdated package.

## Consequences

- Easier: the owner can install directly from the repository; anyone can rebuild and compare.
- Harder: every content change requires a rebuild before committing; the test enforces this. Archive bytes can differ between zlib builds even when contents are identical, so the staleness test compares file contents, not archive bytes.

## Alternatives rejected

- Build on demand only: leaves the owner without an artifact when no build environment is at hand.
- GitHub releases: needs release tooling and the owner's decision on publishing; a sensible next step rather than a version 1 requirement.
