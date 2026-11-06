# RunPod Storage and Billing

What persists, what is billed, and when. Based on RunPod's documentation as found on 2026-11-01 (sources below); RunPod changes products and prices, so re-check before relying on details.

## Storage types

| Type | Lifetime | Typical use | Billing note |
|---|---|---|---|
| Container disk | Cleared when the pod stops or restarts | Scratch space, caches | Billed while the pod runs |
| Volume disk (`/workspace`) | Kept while the pod is stopped; deleted when the pod is terminated | Working files for one pod | Billed while running and while stopped (at a different rate when stopped) |
| Network volume | Independent of pods; survives pod deletion; tied to a data center | Models, datasets, checkpoints shared across pods | Billed for as long as it exists |

Sources found: RunPod storage types documentation (docs.runpod.io, pods storage types page), pricing documentation (docs.runpod.io, pods pricing page), and RunPod's blog guide to storage. One conflict seen: a blog post described moving network volumes between pods, while the storage types documentation said network volumes are attached at pod creation and cannot be detached later. Treat the documentation as authoritative and verify.

## Billing behavior

- Stopping a pod ends GPU charges but storage charges continue (volume disk and network volumes).
- Terminating a pod deletes it and its volume disk; network volumes remain and keep billing.
- If an account balance runs out, RunPod's documentation warns that pods and even network volumes can be terminated and their data lost; RunPod states it keeps no copies of user data.
- Serverless workers bill for the time they run, including startup; idle timeouts and worker caps bound the cost.

## Practices

- Put models and outputs on a network volume or in the image; never rely on container disk.
- Write checkpoints regularly during long jobs.
- Copy important results off RunPod (object storage or the owner's machine).
- Review running pods, endpoints and volumes after every job; delete what is not needed.
- Record prices from the pricing page with the date in every plan (`runpod_tool.py plan --price-source`).
