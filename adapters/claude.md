# Adapter: Claude

**Evidence:** skill loading **executed** in Claude Code (MYCH-PLUGIN 1.0 was installed and invoked through the Skill tool, and `${CLAUDE_SKILL_DIR}` substitution was observed). The Messages API adapter in `chatkit.py` is **stub-tested** only.

## Loading MYCH-HORIZON

- **Claude Code:** copy the skill folders to `.claude/skills/` (project) or `~/.claude/skills/` (user): `python3 tools/mych.py export --host claude-code --project .`. Placeholders are kept, because Claude Code expands `${CLAUDE_SKILL_DIR}`.
- **Other Anthropic surfaces that accept skill uploads:** upload the release ZIPs from `dist/` (one skill per archive, skill folder at the archive root).
- **Messages API without skills:** use a bundle: `python3 tools/mych.py bundle --provider anthropic --task "..."`.

## How each capability is reached

| Capability | How |
|---|---|
| System instructions | Top-level `system` parameter, separate from `messages` |
| Tool definitions | `tools: [{name, description, input_schema}]` |
| Tool calls | Assistant content block `{"type": "tool_use", "id", "name", "input"}` (input is an object) |
| Tool results | Next user message with `{"type": "tool_result", "tool_use_id", "content"}` blocks |
| Structured output | Tool use with an `input_schema` is the portable route; check current docs for dedicated modes |
| Multimodal input | Text, images and PDFs as content blocks (per model) |
| File access | Only through the host's tools (Claude Code has file and shell tools; the bare API has none) |
| Orchestration | Claude Code offers sub-agents; follow [delegation.md](../mych-plugin/systems/delegation.md) |
| Context window | Varies by model and plan; read the current model documentation rather than assuming |

## Notes

- Request headers: `x-api-key` and `anthropic-version: 2023-06-01`.
- Keep untrusted tool output inside `tool_result` blocks; never move it into the system prompt.
- Source: <https://docs.anthropic.com/en/docs/build-with-claude/tool-use> (format as documented; not re-checked against a live API in this repository).
