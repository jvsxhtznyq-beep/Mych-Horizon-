# Provenance, Rights and Safety

What to record about every generated image, which rights questions to settle before generating, and how to report honestly.

## Provenance records

`imagegen.py` writes `NAME.provenance.json` next to every generated image:

| Field | Meaning |
|---|---|
| `backend` | `comfyui`, `openai-images`, or another backend name |
| `endpoint` or `server` | Where the request went (no keys) |
| `model` | Model or checkpoint name as given |
| `prompt`, `negative`, `revised_prompt` | Text sent, and any rewritten prompt the service returned |
| `seed`, `parameters` | Everything needed to reproduce the run, when the backend allows it |
| `sha256`, `bytes`, `file` | Identity of the saved file |
| `created_by` | Tool and version |

Keep sidecars with the images in version control or the asset store. For public distribution, content credential standards such as C2PA can carry provenance inside files; adding them needs separate tooling that is not bundled here.

## Rights checklist before generating

- [ ] The model's license allows the intended use (commercial use, redistribution, attribution requirements).
- [ ] No real person's likeness without consent and a lawful basis.
- [ ] No logos, trademarks or copyrighted characters unless the owner holds the rights.
- [ ] Input images (for image-to-image) are owned by or licensed to the owner.
- [ ] The hosted service's terms allow the use, and its content policy is respected.

When any box cannot be checked, ask the owner before generating.

## Disclosure

- Say when images are AI-generated if the context calls for it (journalism, marketing claims, platforms with disclosure rules).
- In reports, list the backend and model for each delivered image. "Generated with backend X, model Y, seed Z" is a result; "an image was created" is not.

## Honest reporting

- If no backend ran: "No image was generated because no generation backend is available here. Prompts and parameters are ready in prompts.md."
- If a run failed: report the error and that nothing was saved.
- If images were edited after generation: say which processing steps ran (the batch manifest lists them).

## Privacy

- Strip metadata (`process strip`) from photos before publishing; EXIF may contain GPS coordinates, device serials and timestamps.
- Do not send private or personal images to third-party APIs without the owner's approval.
