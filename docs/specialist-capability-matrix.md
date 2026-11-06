# Specialist Capability Matrix

What each domain specialist can do offline, what it needs for live work, how it was tested, and how ready it was in the MYCH-HORIZON test environment (Linux container with Python 3.13, Node.js 22, Pillow, ImageMagick, Playwright with Chromium; no GPU, no Blender, no model or image API keys, no RunPod key). Readiness comes from `detect-capabilities.py`.

| Specialist | Offline tools (standard library unless noted) | Live capability needs | Tests | Status | Readiness here |
|---|---|---|---|---|---|
| `mych-pixel-art` | PNG codec, text sprites, sheet packer with Aseprite-style JSON, palette validator, scaler | None | 12 unit tests incl. Pillow and ImageMagick cross-checks; produced all Glowmoss Caverns sprites | **verified** (used in the game benchmark) | ready |
| `mych-image-generation` | Backend detection, ComfyUI and OpenAI-style clients, provenance sidecars; Pillow processing and batch recipes | A generation backend (GPU with diffusers, a ComfyUI server, or an image API key); spending approval | 10 tests (stub servers; no real service contacted) | tested | partial: no backend, so generation is unavailable and the tool says so |
| `mych-3d-design` | glTF/GLB inspect and validation, primitive generator, STL print checks, OBJ to GLB; Blender templates | Blender for modeling and rendering | 11 tests; generated files pass the Khronos glTF-Validator with no errors or warnings; Blender templates compile-checked only | tested | partial: no Blender |
| `mych-chatbot-engineering` | Agent loop, validated tools, memory, BM25 retrieval, adapters for three API styles, golden-conversation eval (Python and JavaScript) | A model credential or local model runtime | 13 Python tests and 10 Node tests (stub servers); harness end-to-end with a stub model | tested | partial: no model credential |
| `mych-api-integration` | Resilient client, webhook verification (three schemes), OpenAPI verify and diff, stub server | Network access to the target API and its credentials | 18 tests | tested | ready |
| `mych-emoji-language` | Emoji sequence inspector, multi-system lengths, custom emoji asset checks | None | 8 tests | tested | ready |
| `mych-cloud-infrastructure` | Cost estimates from sourced prices, deployment plan review, DNS review, Dockerfile review (all offline) | Cloud credentials and approval for deploying or spending | 8 tests | tested | ready for offline review; a cloud credential variable exists but was never used or tested |
| `mych-runpod` | VRAM estimator, deployment plans with persistence warnings, dry-run serverless client, worker template | `RUNPOD_API_KEY` and spending approval | 5 tests (stub server for the executed path) | tested | partial: no RunPod key |

## Neutral tools per specialist

Each specialist exposes tools for models without skill loading (see `registry/specialists.json`): `mych_pixel_render`, `mych_pixel_validate`, `mych_image_detect`, `mych_image_generate` (requires approval unless a dry run), `mych_image_process`, `mych_3d_inspect`, `mych_3d_make_primitive`, `mych_3d_stl_check`, `mych_chat_eval`, `mych_chat_request_preview`, `mych_api_openapi_verify`, `mych_api_request_preview`, `mych_emoji_inspect`, `mych_emoji_check_asset`, `mych_cloud_check`, `mych_runpod_vram`, `mych_runpod_endpoint_preview`.

## Not executed anywhere yet

- Real image generation (no backend), real Blender runs, real model APIs, real RunPod or cloud calls.
- Each of these is documented as unverified in its specialist and blocked on credentials, hardware or software that the owner can provide.
