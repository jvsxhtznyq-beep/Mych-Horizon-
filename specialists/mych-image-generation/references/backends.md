# Generation Backends

What each kind of backend needs, how to detect it, and what this specialist drives. Prices, model names and limits change often: read the provider's current documentation before quoting them.

## Kinds of backends

| Backend | Needs | Reproducible | Driven by imagegen.py |
|---|---|---|---|
| ComfyUI server (local or self-hosted) | A running server, a checkpoint, an API-format workflow | Yes, with a fixed seed and the same graph, model and versions | Yes (`--backend comfyui`) |
| diffusers library | Python with torch and diffusers, usually an NVIDIA GPU with enough VRAM | Yes, with a fixed seed and deterministic settings | No: write a small diffusers script; `detect` reports readiness |
| Automatic1111-style web UIs | A running server with its API enabled | Yes, with a fixed seed | No: use its documented API or export to ComfyUI |
| OpenAI-style images endpoint | API key, a model name from the provider's docs | Usually not: no seed parameter | Yes (`--backend openai`, `--base-url` for compatible gateways) |
| Other hosted APIs (Google, Stability, Replicate, fal, Black Forest Labs and others) | API key, provider-specific request shapes | Varies | No: `detect` reports the key; build a client with `mych-api-integration` |

## Detecting what exists

`python3 scripts/imagegen.py detect --probe-local` reports:

- `diffusers-local`: torch and diffusers importable **and** an NVIDIA GPU visible to `nvidia-smi`.
- `comfyui`: whether `/system_stats` answers at the server URL (only with `--probe-local`).
- API backends: whether the key variable is set. A set key is not proof that it works; the first real call is.

`generation_available` is true only when a backend that this script can drive is available.

## Local hardware

- Diffusion models need GPU memory roughly in proportion to model size and resolution. Older SD 1.5-class models run in a few GB of VRAM; larger modern models need substantially more. Check the model card for stated requirements rather than guessing.
- CPU-only generation is possible with some pipelines but is typically far too slow for iteration.
- For rented GPUs, see `mych-runpod` (VRAM estimates, persistence, shutdown).

## Choosing a backend

1. Is a backend available here? If not, stop and report.
2. Does the brief need reproducibility or fine control (inpainting masks, ControlNet, LoRA)? Prefer ComfyUI or diffusers.
3. Does it need speed without local hardware? A hosted API, with approved spending.
4. Does the license of the model fit the intended use (commercial, redistribution)? Check before generating.

## Costs and limits

- Hosted APIs charge per image or per compute time and enforce rate limits; estimate before batch runs and handle HTTP 429 with backoff (see `mych-api-integration`).
- Local backends cost electricity and GPU time; rented GPUs bill while running, including idle time.
