# ComfyUI API

How `scripts/imagegen.py --backend comfyui` talks to a ComfyUI server, and how to prepare workflows. The routes below follow ComfyUI's server as commonly documented and used; verify them against the version you run, because this repository's tests use a stub server, not a real ComfyUI instance.

## Routes used

| Route | Method | Purpose |
|---|---|---|
| `/system_stats` | GET | Health and device information (used by `detect --probe-local`) |
| `/prompt` | POST | Queue a workflow: body `{"prompt": GRAPH, "client_id": ID}`; returns `prompt_id` and any `node_errors` |
| `/history/{prompt_id}` | GET | Status and outputs; images appear under `outputs[node_id].images[]` with `filename`, `subfolder`, `type` |
| `/view` | GET | Download an output with query `filename`, `subfolder`, `type` |

ComfyUI also offers a WebSocket (`/ws`) for progress events; the client polls history instead, which is simpler and sufficient for batch work.

## Workflows in API format

- Build the graph in ComfyUI, then export it with the API-format save option. The UI's regular save format is different and will not run through `/prompt`.
- An API-format graph maps node ids to `{"class_type": ..., "inputs": {...}}`; links are `[source_node_id, output_index]`.
- [The bundled template](../assets/comfyui-txt2img-api.json) is the standard text-to-image graph: checkpoint loader, two text encoders (positive and negative), empty latent, KSampler, VAE decode, save image.

## Placeholders

String values that are exactly a placeholder are replaced with typed values; placeholders inside longer strings are replaced as text.

| Placeholder | Filled from |
|---|---|
| `{{PROMPT}}`, `{{NEGATIVE}}` | `--prompt`, `--negative` |
| `{{SEED}}` | `--seed` (random and recorded when omitted) |
| `{{WIDTH}}`, `{{HEIGHT}}` | `--size` |
| `{{STEPS}}`, `{{CFG}}` | `--steps`, `--cfg` |
| `{{CHECKPOINT}}` | `--checkpoint` |

Any placeholder left without a value stops the run before anything is sent.

## Errors

- `node_errors` in the `/prompt` response (missing models, invalid inputs) stop the run with the message shown.
- A history status of `error` stops the run; nothing is saved.
- No outputs before `--timeout` stops the run with a clear message.

## Operating safely

- Bind ComfyUI to localhost or a private network; it has no authentication by default.
- Custom nodes run arbitrary Python code: install only reviewed nodes from trusted sources, and treat workflow files from others as untrusted until their custom nodes are reviewed.
- Large models and outputs fill disks quickly; on rented GPUs, keep models on persistent storage and outputs synced elsewhere.
