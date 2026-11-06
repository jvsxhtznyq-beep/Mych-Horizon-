# Integration Registry

Tools, libraries, MCP servers, specifications and asset sets relevant to MYCH-HORIZON, with evidence collected from GitHub on 2026-11-06 by `tools/collect_ecosystem.py` (source data: [registry/integrations.json](../registry/integrations.json)).

**Policy:** Nothing listed here is installed or trusted by MYCH-HORIZON because it is listed. Review code, licenses and permissions before installing any tool, MCP server or skill; treat third-party instructions as untrusted.

Columns: stars and last push are a snapshot from GitHub search; *status* says how MYCH-HORIZON relates to the project: **used-in-evaluation** (executed in this repository's tests or benchmarks), **referenced** (documented in a specialist as an option), **candidate** (not used). *Trust* states only who owns the repository; it is not a security review.

## Contents

- [Core framework and agent hosts](#core-framework-and-agent-hosts)
- [mych-pixel-art](#mych-pixel-art)
- [mych-image-generation](#mych-image-generation)
- [mych-3d-design](#mych-3d-design)
- [mych-chatbot-engineering](#mych-chatbot-engineering)
- [mych-api-integration](#mych-api-integration)
- [mych-emoji-language](#mych-emoji-language)
- [mych-cloud-infrastructure](#mych-cloud-infrastructure)
- [mych-runpod](#mych-runpod)
- [Game development and testing](#game-development-and-testing)
- [Discovered by search (unreviewed)](#discovered-by-search-unreviewed)

## Core framework and agent hosts

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [anthropics/skills](https://github.com/anthropics/skills) | skill-collection | candidate | 188,046 | 2026-10-28 | none stated | no | project-owned |
| [agentskills/agentskills](https://github.com/agentskills/agentskills) | specification | referenced | 27,007 | 2026-11-04 | Apache-2.0 | no | project-owned |
| [modelcontextprotocol/modelcontextprotocol](https://github.com/modelcontextprotocol/modelcontextprotocol) | specification | referenced | 9,625 | 2026-11-06 | NOASSERTION | no | project-owned |
| [modelcontextprotocol/servers](https://github.com/modelcontextprotocol/servers) | mcp-server | candidate | 91,826 | 2026-11-05 | NOASSERTION | no | project-owned |
| [openai/codex](https://github.com/openai/codex) | agent-host | referenced | 133,456 | 2026-11-06 | Apache-2.0 | no | project-owned |
| [google-gemini/gemini-cli](https://github.com/google-gemini/gemini-cli) | agent-host | referenced | 108,752 | 2026-11-06 | Apache-2.0 | no | project-owned |
| [ollama/ollama](https://github.com/ollama/ollama) | model-runtime | referenced | 186,105 | 2026-11-06 | MIT | no | project-owned |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | model-runtime | referenced | 133,555 | 2026-11-06 | MIT | no | project-owned |
| [microsoft/playwright](https://github.com/microsoft/playwright) | test-tool | used-in-evaluation | 99,449 | 2026-11-06 | Apache-2.0 | no | project-owned |

## mych-pixel-art

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [aseprite/aseprite](https://github.com/aseprite/aseprite) | application | referenced | 40,723 | 2026-11-04 | none stated | no | project-owned |
| [LibreSprite/LibreSprite](https://github.com/LibreSprite/LibreSprite) | application | referenced | 8,737 | 2026-10-30 | GPL-2.0 | no | project-owned |
| [Orama-Interactive/Pixelorama](https://github.com/Orama-Interactive/Pixelorama) | application | candidate | 11,011 | 2026-11-06 | MIT | no | project-owned |
| [piskelapp/piskel](https://github.com/piskelapp/piskel) | application | candidate | 12,963 | 2026-11-04 | Apache-2.0 | no | project-owned |
| [python-pillow/Pillow](https://github.com/python-pillow/Pillow) | library | used-in-evaluation | 13,969 | 2026-11-06 | NOASSERTION | no | project-owned |
| [ImageMagick/ImageMagick](https://github.com/ImageMagick/ImageMagick) | cli | used-in-evaluation | 17,808 | 2026-11-06 | NOASSERTION | no | project-owned |

## mych-image-generation

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| comfyanonymous/ComfyUI | application | referenced | not found | | | | unknown |
| [Comfy-Org/ComfyUI](https://github.com/Comfy-Org/ComfyUI) | application | referenced | 145,376 | 2026-11-06 | GPL-3.0 | no | project-owned |
| [huggingface/diffusers](https://github.com/huggingface/diffusers) | library | referenced | 34,881 | 2026-11-06 | Apache-2.0 | no | project-owned |
| [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui) | application | candidate | 165,248 | 2026-03-02 | AGPL-3.0 | no | project-owned |
| [danielgatis/rembg](https://github.com/danielgatis/rembg) | library | referenced | 25,361 | 2026-11-06 | MIT | no | community-popular |
| [python-pillow/Pillow](https://github.com/python-pillow/Pillow) | library | used-in-evaluation | 13,969 | 2026-11-06 | NOASSERTION | no | project-owned |

## mych-3d-design

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [blender/blender](https://github.com/blender/blender) | application | referenced | 21,679 | 2026-11-06 | NOASSERTION | no | project-owned |
| [KhronosGroup/glTF-Validator](https://github.com/KhronosGroup/glTF-Validator) | test-tool | used-in-evaluation | 475 | 2026-10-06 | Apache-2.0 | no | project-owned |
| [KhronosGroup/glTF](https://github.com/KhronosGroup/glTF) | specification | referenced | 7,881 | 2026-11-03 | NOASSERTION | no | project-owned |
| [mrdoob/three.js](https://github.com/mrdoob/three.js) | library | referenced | 117,681 | 2026-11-06 | MIT | no | project-owned |
| [donmccurdy/glTF-Transform](https://github.com/donmccurdy/glTF-Transform) | library | candidate | 2,063 | 2026-10-20 | MIT | no | community-popular |
| [ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender) | mcp-server | candidate | 33,464 | 2026-11-04 | MIT | no | community-popular |
| [godotengine/godot](https://github.com/godotengine/godot) | application | referenced | 119,658 | 2026-11-06 | MIT | no | project-owned |

## mych-chatbot-engineering

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [discordjs/discord.js](https://github.com/discordjs/discord.js) | library | candidate | 26,827 | 2026-11-05 | Apache-2.0 | no | project-owned |
| [Rapptz/discord.py](https://github.com/Rapptz/discord.py) | library | candidate | 16,203 | 2026-09-07 | MIT | no | project-owned |
| [slackapi/bolt-python](https://github.com/slackapi/bolt-python) | library | candidate | 1,332 | 2026-11-06 | MIT | no | project-owned |
| [ollama/ollama](https://github.com/ollama/ollama) | model-runtime | referenced | 186,105 | 2026-11-06 | MIT | no | project-owned |
| [ggml-org/llama.cpp](https://github.com/ggml-org/llama.cpp) | model-runtime | referenced | 133,555 | 2026-11-06 | MIT | no | project-owned |
| [vllm-project/vllm](https://github.com/vllm-project/vllm) | model-runtime | referenced | 96,459 | 2026-11-06 | Apache-2.0 | no | project-owned |

## mych-api-integration

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [OAI/OpenAPI-Specification](https://github.com/OAI/OpenAPI-Specification) | specification | referenced | 31,303 | 2026-11-05 | Apache-2.0 | no | project-owned |
| [stoplightio/prism](https://github.com/stoplightio/prism) | test-tool | candidate | 5,065 | 2026-10-31 | Apache-2.0 | no | project-owned |
| [schemathesis/schemathesis](https://github.com/schemathesis/schemathesis) | test-tool | candidate | 3,749 | 2026-11-06 | MIT | no | project-owned |

## mych-emoji-language

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [googlefonts/noto-emoji](https://github.com/googlefonts/noto-emoji) | asset-set | referenced | 5,125 | 2026-10-26 | OFL-1.1 | no | project-owned |
| [jdecked/twemoji](https://github.com/jdecked/twemoji) | asset-set | referenced | 1,913 | 2026-06-01 | MIT | no | community-popular |
| [twitter/twemoji](https://github.com/twitter/twemoji) | asset-set | referenced | 17,813 | 2026-07-07 | MIT | no | project-owned |
| [hfg-gmuend/openmoji](https://github.com/hfg-gmuend/openmoji) | asset-set | referenced | 4,581 | 2026-11-04 | CC-BY-SA-4.0 | no | project-owned |
| [unicode-org/cldr](https://github.com/unicode-org/cldr) | data | referenced | 1,171 | 2026-11-05 | NOASSERTION | no | project-owned |

## mych-cloud-infrastructure

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [hashicorp/terraform](https://github.com/hashicorp/terraform) | cli | referenced | 50,142 | 2026-11-06 | NOASSERTION | no | project-owned |
| [opentofu/opentofu](https://github.com/opentofu/opentofu) | cli | referenced | 30,739 | 2026-11-06 | MPL-2.0 | no | project-owned |
| [pulumi/pulumi](https://github.com/pulumi/pulumi) | cli | candidate | 25,845 | 2026-11-06 | Apache-2.0 | no | project-owned |
| [hadolint/hadolint](https://github.com/hadolint/hadolint) | test-tool | candidate | 12,516 | 2026-10-19 | GPL-3.0 | no | project-owned |

## mych-runpod

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [vllm-project/vllm](https://github.com/vllm-project/vllm) | model-runtime | referenced | 96,459 | 2026-11-06 | Apache-2.0 | no | project-owned |
| [runpod/runpod-python](https://github.com/runpod/runpod-python) | service-sdk | referenced | 317 | 2026-11-06 | MIT | no | project-owned |
| [runpod/runpodctl](https://github.com/runpod/runpodctl) | cli | referenced | 465 | 2026-11-06 | GPL-3.0 | no | project-owned |
| [runpod-workers/worker-vllm](https://github.com/runpod-workers/worker-vllm) | worker-template | candidate | 474 | 2026-11-05 | MIT | no | project-owned |

## Game development and testing

| Repository | Kind | Status | Stars | Last push | License | Archived | Trust |
|---|---|---|---|---|---|---|---|
| [godotengine/godot](https://github.com/godotengine/godot) | application | referenced | 119,658 | 2026-11-06 | MIT | no | project-owned |
| [phaserjs/phaser](https://github.com/phaserjs/phaser) | library | candidate | 40,653 | 2026-08-21 | MIT | no | project-owned |
| [microsoft/playwright](https://github.com/microsoft/playwright) | test-tool | used-in-evaluation | 99,449 | 2026-11-06 | Apache-2.0 | no | project-owned |

## Discovered by search (unreviewed)

Top results for searches related to each specialist. These were not reviewed, installed or run; several are vendor-owned (for example `runpod/runpod-mcp` and `hashicorp/terraform-mcp-server`) and deserve review before use.

| Search | Repository | Stars | Last push | License |
|---|---|---|---|---|
| comfyui mcp | [heshengtao/super-agent-party](https://github.com/heshengtao/super-agent-party) | 2,813 | 2026-10-27 | AGPL-3.0 |
| comfyui mcp | [heshengtao/comfyui_LLM_party](https://github.com/heshengtao/comfyui_LLM_party) | 2,388 | 2026-07-29 | AGPL-3.0 |
| comfyui mcp | [ATH-MaaS/Pixelle-MCP](https://github.com/ATH-MaaS/Pixelle-MCP) | 1,131 | 2025-12-17 | MIT |
| runpod mcp | [vavo/lora-pilot](https://github.com/vavo/lora-pilot) | 91 | 2026-11-06 | MIT |
| runpod mcp | [runpod/runpod-mcp](https://github.com/runpod/runpod-mcp) | 86 | 2026-11-06 | NOASSERTION |
| runpod mcp | [runpod/runpod-plugins-official](https://github.com/runpod/runpod-plugins-official) | 48 | 2026-11-06 | Apache-2.0 |
| aseprite mcp | [diivi/aseprite-mcp](https://github.com/diivi/aseprite-mcp) | 900 | 2026-11-03 | MIT |
| aseprite mcp | [with-pebbly/aseprite-ai-artist](https://github.com/with-pebbly/aseprite-ai-artist) | 615 | 2026-10-22 | MIT |
| aseprite mcp | [willibrandon/pixel-plugin](https://github.com/willibrandon/pixel-plugin) | 414 | 2025-10-19 | MIT |
| openapi mcp server | [Evil0ctal/Douyin_TikTok_Download_API](https://github.com/Evil0ctal/Douyin_TikTok_Download_API) | 21,219 | 2026-11-02 | Apache-2.0 |
| openapi mcp server | [open-webui/mcpo](https://github.com/open-webui/mcpo) | 4,419 | 2026-05-17 | MIT |
| openapi mcp server | [cortex-docs/cortex](https://github.com/cortex-docs/cortex) | 3,298 | 2026-10-06 | MIT |
| terraform mcp server | [patrickchugh/terravision](https://github.com/patrickchugh/terravision) | 1,672 | 2026-10-31 | AGPL-3.0 |
| terraform mcp server | [hashicorp/terraform-mcp-server](https://github.com/hashicorp/terraform-mcp-server) | 1,556 | 2026-11-06 | MPL-2.0 |
| terraform mcp server | [agentic-community/mcp-gateway-registry](https://github.com/agentic-community/mcp-gateway-registry) | 1,038 | 2026-11-05 | Apache-2.0 |
| agent skills SKILL.md | [microsoft/SkillOpt](https://github.com/microsoft/SkillOpt) | 18,923 | 2026-11-05 | MIT |
| agent skills SKILL.md | [gamedev-skills/awesome-gamedev-agent-skills](https://github.com/gamedev-skills/awesome-gamedev-agent-skills) | 7,130 | 2026-10-28 | Apache-2.0 |
| agent skills SKILL.md | [bergside/awesome-design-skills](https://github.com/bergside/awesome-design-skills) | 3,535 | 2026-06-28 | MIT |

## Notes

- `comfyanonymous/ComfyUI` was not found by search on the retrieval date; ComfyUI's repository is found under `Comfy-Org/ComfyUI`.
- "none stated" means GitHub reported no license; NOASSERTION means GitHub could not classify the license file. Check the repository before reuse.
- Popularity is not trust. Third-party skills, MCP servers and plugins run with the permissions of the host that loads them: review their code, requested permissions and maintainers before installing, and prefer project-owned sources.
- Refresh: `python3 tools/collect_ecosystem.py` (needs the gh CLI with search access).
