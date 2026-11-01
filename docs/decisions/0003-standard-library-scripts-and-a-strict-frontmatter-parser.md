# 0003. Write the scripts with the standard library only, including a strict frontmatter parser

- Date: 2026-11-01
- Status: Accepted
- Deciders: implementation session

## Context

The scripts run wherever the skill runs. Anthropic's documentation states that Claude API code execution has no network access and no runtime package installation; claude.ai and Claude Code environments vary. Validating YAML frontmatter normally needs a YAML library such as PyYAML, which is not part of the standard library. The specification asks to use only justified dependencies.

## Problem

How can the validator check that frontmatter is valid YAML without depending on an installed YAML library?

## Options

1. **Require PyYAML.** Simple and complete, but fails where PyYAML is missing and cannot be installed.
2. **Standard library only, with a strict parser for the YAML subset skill frontmatter needs, cross-checked against PyYAML when it happens to be installed.**
3. **Vendor a YAML library into the skill.** Large, adds maintenance and license questions.

## Decision

Option 2. `validate-skill.py` contains a strict parser for the constructs skill frontmatter uses (fields, quoted and plain scalars, block scalars, one nested mapping level, simple lists). It rejects what it does not support instead of guessing, flags unquoted values that YAML parsers would turn into booleans, numbers, nulls or dates, and treats duplicate keys as errors. When PyYAML is available, both parsers run and any disagreement is an error. When the strict parser rejects something PyYAML accepts, the validator reports a warning and continues with PyYAML's result. All four scripts target Python 3.8 or newer and use no third-party packages.

## Reasoning

The subset parser works everywhere, and the PyYAML cross-check catches divergence where both exist. Being stricter than general YAML is a feature for frontmatter: constructs that different loaders might read differently are flagged before upload.

## Consequences

- Easier: scripts run in restricted sandboxes; no installation step.
- Harder: the parser is code to maintain; unusual but valid YAML may produce warnings.
- Verification: unit tests compare the parser with PyYAML on representative inputs and run the full suite with PyYAML hidden. The scripts were executed on Python 3.13 and checked against the Python 3.8 grammar; they were not executed on a Python 3.8 interpreter in this environment.

## Alternatives rejected

- Requiring PyYAML: breaks in environments without it.
- Vendoring a YAML library: disproportionate size and maintenance for the need.
