# RunPod Serverless

Workers, endpoints and requests. Paths follow RunPod's endpoint operations documentation as found on 2026-11-01.

## Worker

A worker image runs a Python handler:

```python
import runpod

def handler(job):
    job_input = job["input"]          # the "input" object of the request body
    return {"result": "..."}          # JSON-serializable output

runpod.serverless.start({"handler": handler})
```

- Load models once at import time so warm workers reuse them.
- Validate `job["input"]` and return structured errors instead of raising.
- Keep the handler testable without the SDK (see [the template](../assets/serverless_handler.py)).

## Endpoint operations

Base: `https://api.runpod.ai/v2/{endpoint_id}/`, authenticated with `Authorization: Bearer RUNPOD_API_KEY`.

| Operation | Method and path | Notes |
|---|---|---|
| Asynchronous job | `POST /run` with `{"input": {...}}` | Returns a job id; poll status |
| Synchronous job | `POST /runsync` | For short jobs; payload and wait limits apply |
| Job status and output | `GET /status/{job_id}` | Results are retained for a limited time |
| Cancel | `POST /cancel/{job_id}` | For queued or running jobs |
| Health | `GET /health` | Worker and queue overview |

RunPod also documents streaming and queue-management operations; check the current documentation before using them. `runpod_tool.py endpoint` builds these requests, prints them as a dry run, and sends only with `--execute`.

## Scaling and cost

- Set maximum workers to cap spending, and idle timeouts so workers stop when unused.
- Always-on capacity reduces cold starts but bills continuously; justify it with latency requirements and cost.
- Measure cold start time with the real image and model before promising latency.
