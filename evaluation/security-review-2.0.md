# Security Review: MYCH-HORIZON 2.0

Review of everything added or changed in 2.0, against the brief's security rules (least privilege, secure credential handling, explicit approval for restricted actions, no unauthorized destructive operations, no weakened controls, no secrets in logs or reports, external content treated as untrusted, no unapproved production changes). Date: 2026-11-06. Reviewer: the building agent (self-review; an independent review is recommended before production use).

## Automated scans

| Check | Command (summary) | Result |
|---|---|---|
| Shell execution, `eval`/`exec`, unsafe deserialization in Python | `grep -E "shell=True|os.system|eval(|exec(|pickle|yaml.load("` over skills and tools | No uses. One match is the scanner's file-extension pattern for detecting `.pkl` data files |
| TLS verification disabled | `grep -E "verify=False|CERT_NONE|_create_unverified_context|rejectUnauthorized|NODE_TLS_REJECT"` | None |
| Secret-looking literals in tracked files | Patterns for AWS keys, GitHub tokens, Slack tokens, private keys, long `sk-` keys | None. Test fixtures use obviously fake values (`sk-test-DO-NOT-PRINT-...`, `rp-secret-key-value`) to prove they are never printed |
| DOM injection sinks in the game and JavaScript kit | `innerHTML`, `outerHTML`, `insertAdjacentHTML`, `document.write`, `new Function`, `eval` | None; the game writes text with `textContent` |
| Subprocess calls | All `subprocess` uses listed | Six call sites, all with fixed argument lists and timeouts: `detect-capabilities.py` (version probes, `nvidia-smi`, `npm root -g`), `scan-project.py` (read-only git), `imagegen.py` (`nvidia-smi -L`), `collect_ecosystem.py` (`gh api` search), `mych.py run-tool` (argument lists built from vetted templates) |
| Development artifacts in skill folders | `__pycache__`, `.pyc`, `.DS_Store` | None |

## Design review

| Area | Control | Verified by |
|---|---|---|
| Credentials | Read from environment variables only; never printed; names reported, values never read out (`detect-capabilities.py`); keys redacted from errors, dry runs, logs and provenance files (`chatkit`, `imagegen`, `apiclient`, `runpod_tool`) | Tests that set a recognizable fake secret and assert it never appears in output |
| Spending and external actions | Paid generation and RunPod calls are dry runs by default; `run-tool` refuses `requires_approval` tools unless approved or a dry run; the ledger gates tasks with `--needs-approval` | `test_tools_that_spend_money_need_approval`; RunPod dry-run tests; ledger approval tests |
| Tool confinement for models | `run-tool` runs argument lists (no shell), confines path parameters to the workspace, forbids redirecting the ledger with `--file`, caps output size and time | `test_run_tool_refuses_paths_outside_the_workspace_and_forbidden_arguments` |
| Server-side request forgery | The API client refuses absolute URLs to other origins | `test_refuses_absolute_urls_to_other_origins` |
| Webhooks | HMAC with constant-time comparison and replay windows | Webhook tests, including a source check for `hmac.compare_digest` |
| Untrusted content | Retrieved text fenced as data in the chatbot kit; asset files parsed, never executed; glTF external buffers restricted to the asset folder; integration registry states that listing is not trust | Retrieval and glTF traversal tests |
| Local configuration reads | `detect-capabilities.py` reads host config files only to list MCP server names; arguments and environment blocks are never output | `test_skills_and_mcp_names_without_their_configuration` |
| Game | No network access; save data validated and repaired; errors shown without stack traces; no third-party scripts | Storage and end-to-end failure tests |
| Supply chain | Skills and tools use only the Python standard library; the game has no runtime dependencies. The Khronos glTF-Validator and Playwright were used only as test tools outside the repository, with install scripts disabled for the validator | Repository contents |

## Residual risks

1. **Approval records are claims.** The ledger records who approved, as reported by the agent; it cannot prove a person approved. Documented in `systems/task-management.md`.
2. **Host configuration files are read into memory.** Capability detection reads files such as `~/.claude.json` to list MCP server names. Values are never output, but a compromised process could read the same files; run detection only where the agent is already trusted.
3. **Heuristic evidence rules.** The ledger's failure-marker detection can produce false positives (observed once in this build: evidence that quoted an expected "exit 3"), resolved with a recorded `--override`.
4. **Untested live paths.** Real image APIs, ComfyUI servers, RunPod and cloud calls were never executed; their clients were tested against stubs of documented shapes.
5. **Inline script in the game build.** The single-file build cannot use a strict Content Security Policy without script hashes; it loads no external resources.

## Conclusion

No vulnerabilities were found by the scans or the design review. The residual risks above are documented where they apply, and none weakens a control from 1.0.
