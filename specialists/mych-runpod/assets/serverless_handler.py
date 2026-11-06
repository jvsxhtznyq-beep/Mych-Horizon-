"""Template for a RunPod serverless worker.

The handler receives a job dictionary whose "input" holds the request body's
"input" object, and returns JSON-serializable output. The worker starts with
runpod.serverless.start({"handler": handler}) from RunPod's Python SDK,
which is installed in the worker image. The handler itself is plain Python,
so it can be unit-tested locally without the SDK:

    from serverless_handler import handler
    print(handler({"id": "local-test", "input": {"prompt": "hello"}}))

Load models once at import time (outside the handler) so warm workers reuse
them, and keep model files on a network volume or baked into the image.
"""

import time

MAX_PROMPT_CHARS = 4000
MODEL = None  # load your model here once, for example from /runpod-volume or the image


def validate(job_input):
    if not isinstance(job_input, dict):
        return "input must be a JSON object"
    prompt = job_input.get("prompt")
    if not isinstance(prompt, str) or not prompt.strip():
        return "input.prompt must be a non-empty string"
    if len(prompt) > MAX_PROMPT_CHARS:
        return "input.prompt is longer than {} characters".format(MAX_PROMPT_CHARS)
    return None


def handler(job):
    started = time.time()
    job_input = job.get("input")
    problem = validate(job_input)
    if problem:
        return {"error": problem}
    prompt = job_input["prompt"].strip()
    # Replace this echo with real inference using MODEL.
    result = {"echo": prompt, "characters": len(prompt)}
    return {"output": result, "job_id": job.get("id"), "seconds": round(time.time() - started, 3)}


if __name__ == "__main__":
    import runpod  # provided in the worker image

    runpod.serverless.start({"handler": handler})
