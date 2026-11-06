# Roadmap

Planned work after MYCH-HORIZON 2.0, ordered by value. Items marked **blocked** need something the test environment did not have.

## Next

1. **Cross-model runs (blocked: no API keys or local runtime).** Run the harness, the chatbot golden set and one benchmark task with GPT, Gemini, GLM and an open-weight model; record transcripts; update the [model compatibility matrix](model-compatibility-matrix.md).
2. **Live specialist runs (blocked: hardware and credentials).** Generate images through a real ComfyUI or API backend; run the Blender templates; make one approved, low-cost RunPod serverless call; run one read-only cloud inventory.
3. **Continuous integration.** Run the unit suites, `validate-all --strict`, `registry-check` and the game's unit tests on every push; run the Playwright suite nightly.
4. **Additional benchmarks** from the 2.0 brief: a chatbot platform (retrieval plus tools), a 3D asset pipeline (model to validated GLB in an engine), a cloud deployment plan review, an API platform with contract tests, and a pixel-art pipeline at scale.

## Later

- Game benchmark follow-ups: Firefox and Safari runs, real gamepads and phones, audio review by a person, more caverns, key remapping, an accessibility audit.
- Routing: learn from recorded routing outcomes; keep the heuristic router explainable.
- Ledger: optional signed approvals, so an approval record can be tied to a person rather than an agent's claim.
- Registry: scheduled refresh of `integrations.json`; security review notes for the most relevant MCP servers.
- More adapters through the OpenAI-compatible path (for example additional open-weight servers), each with evidence levels.
