# Prompting Image Models

How to write prompts and choose parameters that produce usable images, and how to iterate efficiently.

## Prompt structure

Order from most to least important:

1. **Subject:** what is in the image, with concrete nouns and a clear count ("one red fox").
2. **Action and composition:** pose, framing, camera angle, distance ("three-quarter view, centered, full body").
3. **Style or medium:** "watercolor", "isometric low-poly render", "flat vector illustration".
4. **Lighting and mood:** "soft overcast light", "rim light, teal and amber".
5. **Palette and detail level:** "muted earth tones", "minimal background".

Prefer specific descriptions to stacks of adjectives. Avoid contradictory instructions.

## Negative prompts

Diffusion models accept a negative prompt listing what to avoid ("blurry, extra fingers, watermark, text"). Keep it short and specific to observed problems; huge generic lists can wash out results. Hosted APIs without a negative prompt field need positive phrasing instead ("clean background").

## Parameters

| Parameter | Effect | Starting point |
|---|---|---|
| Seed | Fixes the initial noise; same seed and settings reproduce an image | Fix it while iterating |
| Steps | More steps refine detail with diminishing returns | 20 to 30 for common samplers |
| Guidance (CFG) | How strongly the prompt is followed; too high oversaturates | Around 5 to 8 for many models |
| Size | Stay near the model's native resolution and aspect ratio | Use the model card's sizes |
| Denoise or strength (image-to-image) | How far the result may move from the input | 0.3 to 0.6 to keep structure |

Exact best values depend on the model and sampler; follow the model card when it gives recommendations.

## Iterating

- Change one thing at a time with a fixed seed, so the effect of the change is visible.
- Generate small batches with different seeds to explore, then lock the best seed.
- Keep a log (the provenance sidecars do this automatically).

## Consistency across a set

- Reuse seeds and shared prompt fragments for style.
- Use reference-image conditioning (IP-Adapter style tools), LoRA adapters or ControlNet in ComfyUI for consistent characters or layouts.
- Fix the palette in post-processing when exact brand colors matter.

## Known model weaknesses

- Text rendering is unreliable in many models: add text afterwards.
- Hands, counts of objects and precise spatial relations often fail; inspect and inpaint.
- Fine repeated patterns can drift; tileable textures need dedicated settings or post-processing.
