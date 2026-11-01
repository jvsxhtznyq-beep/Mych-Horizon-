# Adapter: GLM

**Evidence:** the endpoint and OpenAI-compatible format come from **secondary sources** (integration guides), not from the vendor reference, which was not retrieved. The OpenAI-style adapter in `chatkit.py` is **stub-tested** only. **No GLM model has run MYCH-HORIZON in this repository**: behavior with the framework is untested.

## Loading MYCH-HORIZON

- No native `SKILL.md` loading was found for GLM's own products. Use a bundle (`python3 tools/mych.py bundle --provider glm --task "..."`), the harness, or a host that reads skills and can call GLM.

## How each capability is reached

| Capability | How |
|---|---|
| Endpoint | `https://open.bigmodel.cn/api/paas/v4/chat/completions` (China mainland) or `https://api.z.ai/api/paas/v4/chat/completions` (international); keys are reported not to be interchangeable |
| System instructions | `system` message |
| Tool definitions, calls and results | OpenAI-compatible: `tools`, `tool_calls`, `role: tool` messages |
| Structured output | Treat as unverified; request JSON through a tool and validate it |
| Multimodal input | Vision models only |
| File access and orchestration | Through the host or harness |
| Context window | Varies by model; check the vendor documentation |

## Notes

- Tool-calling reliability is reported to differ between full and lighter model variants (secondary source). Run the harness's evaluation before relying on a model.
- Sources: <https://docs.jambonz.org/guides/features/bring-your-own-llm/zai>, <https://developers.llamaindex.ai/python/framework-api-reference/llms/zhipuai/> (retrieved 2026-11-01).
