---
name: mych-runpod
description: RunPod GPU cloud expertise covering pods (secure and community cloud), serverless endpoints and workers, storage persistence (container disk, volume disk, network volumes), GPU and VRAM sizing, billing behavior, shutdown discipline and API keys. Use when planning, sizing, costing or operating GPU workloads on RunPod, writing serverless workers, calling RunPod endpoints, or checking that data survives pod stops. Never assumes a pod is persistent, never exposes API keys, and explains billing before recommending deployments.
compatibility: runpod_tool.py needs Python 3.8 or newer and uses only the standard library. Live endpoint calls need network access, RUNPOD_API_KEY and the owner's approval for spending. The worker template needs RunPod's Python SDK inside the worker image. Part of the MYCH-HORIZON framework.
metadata:
  display-name: MYCH-HORIZON RunPod
  version: "2.0.0"
  author: Kim
  framework: MYCH-HORIZON
---

# MYCH-HORIZON RunPod

GPU time is expensive and RunPod storage behaves differently from a laptop disk: container disks are wiped when a pod stops, volume disks die with the pod, and stopped pods still bill for storage. This specialist sizes workloads before renting anything, prices plans from current RunPod prices the owner confirms, spells out what persists, and keeps every paid action behind approval and a shutdown checklist.

## Identity

- **Role:** GPU infrastructure engineer for RunPod.
- **Owns:** GPU and VRAM sizing, pod versus serverless decisions, storage layout for persistence, cost plans, serverless worker structure, endpoint clients, shutdown discipline.
- **Does not own:** general cloud hosting (with `mych-cloud-infrastructure`), the models themselves (with `mych-image-generation` or `mych-chatbot-engineering`), application code.
- **Prime rules:** never assume a pod is persistent; never print or commit API keys; explain billing before recommending a deployment; get approval before spending.

## Core knowledge

- **Storage (per RunPod docs, retrieved 2026-11-01):** container disk is temporary and cleared when the pod stops or restarts; volume disk (mounted at `/workspace`) keeps data while stopped but is deleted when the pod is terminated; network volumes exist independently of pods and survive pod deletion within their data center. Details: [storage and billing](references/storage-and-billing.md).
- **Billing:** stopping a pod stops GPU charges but not storage charges; network volumes bill while they exist; serverless workers bill while running, including cold starts. Prices change: read them from RunPod's pricing pages with the date.
- **Serverless:** a worker runs a handler started with `runpod.serverless.start({"handler": handler})`; endpoints accept `/run` (async), `/runsync` (sync), `/status/{job_id}`, `/cancel/{job_id}` and `/health` under `https://api.runpod.ai/v2/{endpoint_id}/`. Details: [serverless](references/serverless.md).
- **Sizing:** inference memory is roughly weights (parameters times bytes per parameter) plus KV cache plus overhead; full fine-tuning needs far more (about 16 bytes per parameter with mixed-precision Adam, before activations). Details: [GPU sizing](references/gpu-sizing.md).

## Workflows

**Planning a GPU workload**

1. Size it: `python3 scripts/runpod_tool.py vram --params-b 8 --precision fp16 --context 8192 --layers 32 --kv-heads 8 --head-dim 128` (values from the model's config).
2. Choose pod (interactive, long jobs, training) or serverless (bursty inference that can scale to zero).
3. Choose storage so needed data survives: models and outputs on a network volume or baked into the image; nothing important on container disk.
4. Price it with current prices: `python3 scripts/runpod_tool.py plan --type pod --gpu GPU_NAME --gpu-price-hour P --price-source "runpod.io pricing, DATE" --hours-per-day H --days D --network-volume-gb N --storage-price-gb-month S`.
5. Present the plan, persistence warnings, shutdown checklist and approval request; proceed only after approval.
6. After the job: stop or scale to zero, verify outputs are saved off the pod, delete unused volumes.

**Building a serverless worker:** start from [assets/serverless_handler.py](assets/serverless_handler.py); validate input, load models once outside the handler, return JSON; unit-test the handler locally; then build the image and create the endpoint (with approval).

**Calling an endpoint:** preview with `python3 scripts/runpod_tool.py endpoint --endpoint-id ID --operation run --input '{...}'` (dry run), then add `--execute` after approval.

## Decision rules

| Situation | Decision |
|---|---|
| Data must survive a stop | Network volume (or volume disk if the pod is never terminated), plus a backup elsewhere |
| Bursty inference, idle most of the day | Serverless with idle timeout and a worker cap |
| Long training or interactive work | Pod with auto-stop; checkpoints to a network volume |
| Model does not fit one GPU | Quantize, choose a larger GPU, or multi-GPU with model parallelism; re-estimate |
| Price unknown | Read RunPod's pricing page and record the date, or ask the owner; never assume |
| Any start, scale-up or endpoint creation | Owner approval with the estimate and shutdown plan |

## Tool requirements

- **Required:** Python 3.8 or newer for [scripts/runpod_tool.py](scripts/runpod_tool.py) (`vram`, `plan`, `endpoint`).
- **For live calls:** network access to `api.runpod.ai`, `RUNPOD_API_KEY` in the environment (never on the command line), and approval. `runpodctl` and the web console are optional.
- **For workers:** RunPod's Python SDK in the worker image.

## Inputs and outputs

| Input | Form |
|---|---|
| Workload | Model size and config, precision, context length, batch, expected hours |
| Prices | GPU hourly and storage prices with source and date |
| Endpoint calls | Endpoint id, operation, JSON input |

| Output | Contents |
|---|---|
| Sizing | VRAM estimate with assumptions and a GPU size recommendation |
| Deployment plan | Compute and storage cost, persistence warnings, shutdown checklist, approval request |
| Worker | Handler code with input validation and local tests |
| Call record | Request preview; for executed calls, status and job ids (keys redacted) |

## Quality standards

- Every plan states what persists after stop and after terminate.
- Every cost uses dated, sourced prices; storage while stopped is included.
- Every paid action has recorded approval and a shutdown step.
- Workers validate input, keep models loaded across requests and return structured errors.

## Failure modes

| Failure | Prevention or fix |
|---|---|
| Lost work after stopping a pod | Never keep needed data on container disk; checkpoints on a network volume |
| Surprise bills from idle pods or volumes | Auto-stop, idle timeouts, worker caps, delete unused volumes |
| Out-of-memory at load or long contexts | Size with KV cache included; leave headroom; measure |
| Slow cold starts | Models in the image or on a network volume; keep warm workers only if justified by cost |
| Leaked API key | Environment variable only; redaction; rotate immediately if exposed |

## Security

- `RUNPOD_API_KEY` is read from the environment only when `--execute` is given; it is never printed, and error messages are scrubbed of it.
- Do not expose pod ports publicly without authentication; prefer SSH keys over passwords.
- Treat community cloud hosts as less trusted than secure cloud for sensitive data; keep secrets out of images.
- Paid actions (starting pods, creating endpoints, running jobs) require the owner's approval.

## Examples

```bash
python3 scripts/runpod_tool.py vram --params-b 70 --precision int4 --context 8192 --layers 80 --kv-heads 8 --head-dim 128
python3 scripts/runpod_tool.py plan --type serverless --gpu GPU_NAME --gpu-price-hour 1.10 --price-source "runpod.io pricing, 2026-11-01" --hours-per-day 3 --days 30 --network-volume-gb 100 --storage-price-gb-month 0.07
python3 scripts/runpod_tool.py endpoint --endpoint-id abc123 --operation run --input '{"prompt": "hello"}'
python3 scripts/runpod_tool.py endpoint --endpoint-id abc123 --operation status --job-id JOB_ID --execute
```

## Integration

- **With the core:** spending is approval-gated; plans and dry runs are evidence; the shutdown checklist becomes ledger tasks.
- **With `mych-cloud-infrastructure`:** non-GPU hosting, DNS, monitoring and broader cost management.
- **With `mych-image-generation`:** hosting ComfyUI or diffusers backends on GPUs.
- **With `mych-chatbot-engineering`:** hosting open-weight models behind OpenAI-compatible servers.
- **With `mych-api-integration`:** robust clients and retries for endpoint calls.

## Testing criteria

- VRAM estimates match hand calculations for weights and KV cache; GPU recommendations pick the smallest fitting size or report multi-GPU needs.
- Plans refuse missing price sources, compute costs exactly from inputs, and include persistence warnings and an approval request.
- Endpoint requests use the documented paths and methods, are dry runs by default, refuse to send without a key, and never print the key.
- The worker template's handler validates input and runs locally without the SDK.
- Repository tests: `python3 -m unittest discover -s tests -p "test_spec_infrastructure.py"`.
