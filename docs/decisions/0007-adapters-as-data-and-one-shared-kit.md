# 0007. Provider adapters are data plus one shared kit

- Status: accepted
- Date: 2026-11-01

## Context

The framework must run on models from several providers without duplicating itself per model. Providers differ in how instructions, tools, tool calls and tool results are encoded, and in which hosts load skills natively.

## Decision

- The core and specialists stay provider-neutral and describe capabilities, not vendor tools.
- Provider differences live in `registry/providers.json` (endpoints, auth, formats, evidence) and short `adapters/*.md` notes.
- Tool definitions are written once in a portable JSON Schema subset and translated by `tools/mych.py` per provider.
- HTTP adapters for the three API styles live once, in the chatbot specialist's `chatkit.py`, which the harness reuses.

## Consequences

- Adding a provider is mostly data; a new API style needs one adapter class and stub tests.
- The chatbot specialist is a dependency of the harness; the harness fails clearly if it is missing.
- Stub tests prove our encoding of documented shapes, not provider behavior; compatibility claims follow decision 0008.
