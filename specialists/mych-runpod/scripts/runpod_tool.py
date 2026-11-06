#!/usr/bin/env python3
"""RunPod planning tools: VRAM estimates, deployment plans with cost and persistence warnings,
and a serverless endpoint client that is dry-run by default (standard library only).

Commands:
  vram --params-b 8 --precision fp16 [--context 8192 --batch 1 --layers 32 --kv-heads 8 --head-dim 128]
       [--mode inference|lora|full] [--gpu-sizes 16,24,48,80]
  plan --type pod|serverless --gpu NAME --gpu-price-hour P --price-source TEXT [--hours-per-day H --days D]
       [--container-disk-gb N --volume-gb N --network-volume-gb N --storage-price-gb-month P]
  endpoint --endpoint-id ID --operation run|runsync|status|cancel|health [--job-id J] [--input JSON]
       [--execute] [--base-url URL]

Facts about storage and billing follow RunPod's documentation as retrieved
on 2026-11-01 (see references/storage-and-billing.md); prices are always
supplied by the user. The endpoint client prints the request and sends
nothing unless --execute is given, and then reads RUNPOD_API_KEY from the
environment. Running jobs costs money: get the owner's approval first.
Exit status: 0 success, 1 failed request or invalid plan, 2 usage error.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Dict, List, Optional, Sequence

BYTES_PER_PARAM = {"fp32": 4.0, "fp16": 2.0, "bf16": 2.0, "fp8": 1.0, "int8": 1.0, "int4": 0.5}
GIB = 1024 ** 3
SERVERLESS_BASE = "https://api.runpod.ai/v2"
OPERATIONS = {"run": ("POST", "run"), "runsync": ("POST", "runsync"), "status": ("GET", "status/{job_id}"),
              "cancel": ("POST", "cancel/{job_id}"), "health": ("GET", "health")}
PERSISTENCE = [
    "Container disk is temporary: it is cleared when the pod stops or restarts. Keep nothing there you need.",
    "Volume disk (mounted at /workspace) keeps data while the pod is stopped, but is deleted when the pod is terminated.",
    "Network volumes exist independently of pods and survive pod deletion; they are tied to a data center.",
    "Stopping a pod stops GPU charges but not storage charges; terminating deletes the pod and its volume disk.",
    "RunPod states it does not keep copies of your data: back up anything important elsewhere.",
]


class RunPodError(Exception):
    pass


def estimate_vram(params_b: float, precision: str, mode: str = "inference", context: int = 4096, batch: int = 1,
                  layers: Optional[int] = None, kv_heads: Optional[int] = None, head_dim: Optional[int] = None,
                  kv_precision: str = "fp16", overhead: float = 0.2) -> Dict[str, Any]:
    if params_b <= 0 or precision not in BYTES_PER_PARAM or kv_precision not in BYTES_PER_PARAM:
        raise RunPodError("params must be positive; precision one of {}".format(", ".join(BYTES_PER_PARAM)))
    params = params_b * 1e9
    weights = params * BYTES_PER_PARAM[precision]
    assumptions = ["weights: {:.0f} B parameters x {} bytes ({})".format(params, BYTES_PER_PARAM[precision], precision)]
    kv = 0.0
    if layers and kv_heads and head_dim:
        kv = 2 * layers * kv_heads * head_dim * context * batch * BYTES_PER_PARAM[kv_precision]
        assumptions.append("KV cache: 2 x {} layers x {} KV heads x {} head dim x {} tokens x batch {} x {} bytes".format(
            layers, kv_heads, head_dim, context, batch, BYTES_PER_PARAM[kv_precision]))
    else:
        assumptions.append("KV cache not estimated: pass --layers, --kv-heads and --head-dim from the model config")
    if mode == "full":
        training = params * 16.0
        assumptions.append("full fine-tuning with mixed-precision Adam: about 16 bytes per parameter for weights, "
                           "gradients and optimizer states (activations not included)")
        base = training + kv
    elif mode == "lora":
        adapter = params * 0.02
        base = weights + adapter * (2 + 2 + 12) + kv
        assumptions.append("LoRA: frozen base weights plus adapters of about 2% of parameters with optimizer states "
                           "(activations not included)")
    else:
        base = weights + kv
    total = base * (1 + overhead)
    assumptions.append("overhead factor {:.0%} for runtime buffers and fragmentation (a rough allowance)".format(overhead))
    return {"mode": mode, "weights_gib": round(weights / GIB, 2), "kv_cache_gib": round(kv / GIB, 2),
            "total_gib": round(total / GIB, 2), "assumptions": assumptions,
            "note": "Estimates are a starting point: measure real usage on a small instance before committing."}


def recommend_gpu(total_gib: float, sizes: List[float]) -> Dict[str, Any]:
    fitting = sorted(size for size in sizes if size >= total_gib)
    if fitting:
        return {"single_gpu_gib": fitting[0], "gpus_needed": 1}
    largest = max(sizes)
    count = int(-(-total_gib // largest))
    return {"single_gpu_gib": None, "gpus_needed": count, "per_gpu_gib": largest,
            "note": "does not fit one GPU; needs model parallelism across {} GPUs of {} GB, or quantization".format(
                count, largest)}


def build_plan(args: argparse.Namespace) -> Dict[str, Any]:
    errors: List[str] = []
    if not args.price_source:
        errors.append("--price-source is required: state where the GPU price came from and when")
    hours = args.hours_per_day * args.days
    compute = args.gpu_price_hour * hours * args.gpu_count
    storage_rate = args.storage_price_gb_month
    storage_lines = []
    storage_total = 0.0
    months = args.days / 30.0
    for label, size in (("container disk", args.container_disk_gb), ("volume disk", args.volume_gb),
                        ("network volume", args.network_volume_gb)):
        if size:
            if storage_rate is None:
                errors.append("--storage-price-gb-month is required when storage is planned")
                break
            cost = size * storage_rate * months
            storage_total += cost
            storage_lines.append({"storage": label, "gb": size, "cost": round(cost, 2)})
    warnings = list(PERSISTENCE)
    if args.type == "pod" and args.container_disk_gb and not (args.volume_gb or args.network_volume_gb):
        warnings.insert(0, "Only container disk is planned: all data is lost when the pod stops.")
    if args.type == "serverless":
        warnings.insert(0, "Serverless workers bill while they run (including cold starts); set idle timeouts and "
                           "maximum workers, and keep models on a network volume or in the image.")
    checklist = ["Owner approved the estimated spend.", "Data that must survive is on a network volume or backed up.",
                 "Auto-stop or idle timeout configured.", "Pod or endpoint stopped or scaled to zero after the job.",
                 "Unused volumes and network volumes deleted when no longer needed (they keep billing).",
                 "API keys stored as secrets, never in images, logs or code."]
    approval = ("Approval needed: run {} x {} on RunPod ({}) for about {:.0f} GPU hours.\n"
                "Estimated cost: {:.2f} for compute plus {:.2f} for storage, using prices from: {}.\n"
                "Risk: charges continue until stopped; container disk is erased on stop.\n"
                "Safeguard: idle timeout, stop after the job, data on a network volume.").format(
        args.gpu_count, args.gpu, args.type, hours * args.gpu_count, compute, storage_total, args.price_source or "UNKNOWN")
    return {"type": args.type, "gpu": args.gpu, "gpu_count": args.gpu_count, "gpu_hours": hours * args.gpu_count,
            "compute_cost": round(compute, 2), "storage": storage_lines, "storage_cost": round(storage_total, 2),
            "total_cost": round(compute + storage_total, 2), "price_source": args.price_source,
            "persistence_and_billing": warnings, "shutdown_checklist": checklist, "approval_request": approval,
            "errors": errors, "ok": not errors}


def endpoint_request(args: argparse.Namespace) -> Dict[str, Any]:
    method, template = OPERATIONS[args.operation]
    if "{job_id}" in template:
        if not args.job_id:
            raise RunPodError("--job-id is required for {}".format(args.operation))
        template = template.format(job_id=urllib.parse.quote(args.job_id, safe=""))
    base = (args.base_url or SERVERLESS_BASE).rstrip("/")
    url = "{}/{}/{}".format(base, urllib.parse.quote(args.endpoint_id, safe=""), template)
    body = None
    if method == "POST" and args.operation in ("run", "runsync"):
        try:
            body = {"input": json.loads(args.input or "{}")}
        except ValueError as exc:
            raise RunPodError("--input must be JSON: {}".format(exc)) from exc
    return {"method": method, "url": url, "headers": {"Authorization": "Bearer $RUNPOD_API_KEY",
                                                      "Content-Type": "application/json"}, "body": body}


def send(request: Dict[str, Any], timeout: float) -> Dict[str, Any]:
    key = os.environ.get("RUNPOD_API_KEY")
    if not key:
        raise RunPodError("RUNPOD_API_KEY is not set; nothing was sent")
    data = json.dumps(request["body"]).encode() if request["body"] is not None else (b"{}" if request["method"] == "POST" else None)
    http_request = urllib.request.Request(request["url"], data=data, method=request["method"],
                                          headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(http_request, timeout=timeout) as response:
            return {"status": response.status, "body": json.loads(response.read().decode() or "null")}
    except urllib.error.HTTPError as exc:
        detail = exc.read(1000).decode("utf-8", "replace").replace(key, "[REDACTED]")
        raise RunPodError("{} {} returned HTTP {}: {}".format(request["method"], request["url"], exc.code, detail)) from exc
    except (urllib.error.URLError, OSError) as exc:
        raise RunPodError("request failed: {}".format(getattr(exc, "reason", exc))) from exc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="RunPod planning tools.", formatter_class=argparse.RawDescriptionHelpFormatter,
                                     epilog=__doc__)
    sub = parser.add_subparsers(dest="command", metavar="COMMAND")
    sub.required = True
    p = sub.add_parser("vram", help="estimate GPU memory for a model")
    p.add_argument("--params-b", type=float, required=True, help="parameters in billions")
    p.add_argument("--precision", choices=tuple(BYTES_PER_PARAM), default="fp16")
    p.add_argument("--mode", choices=("inference", "lora", "full"), default="inference")
    p.add_argument("--context", type=int, default=4096)
    p.add_argument("--batch", type=int, default=1)
    p.add_argument("--layers", type=int)
    p.add_argument("--kv-heads", type=int)
    p.add_argument("--head-dim", type=int)
    p.add_argument("--kv-precision", choices=tuple(BYTES_PER_PARAM), default="fp16")
    p.add_argument("--overhead", type=float, default=0.2)
    p.add_argument("--gpu-sizes", default="16,24,32,48,80,96,141", help="GPU memory sizes in GB to choose from")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("plan", help="deployment plan with cost, persistence warnings and an approval request")
    p.add_argument("--type", choices=("pod", "serverless"), required=True)
    p.add_argument("--gpu", required=True, help="GPU type name as listed by RunPod")
    p.add_argument("--gpu-count", type=int, default=1)
    p.add_argument("--gpu-price-hour", type=float, required=True, help="price per GPU hour from RunPod's pricing page")
    p.add_argument("--price-source", help="where and when the price was read, for example 'runpod.io pricing, 2026-11-01'")
    p.add_argument("--hours-per-day", type=float, default=24)
    p.add_argument("--days", type=float, default=30)
    p.add_argument("--container-disk-gb", type=float, default=0)
    p.add_argument("--volume-gb", type=float, default=0)
    p.add_argument("--network-volume-gb", type=float, default=0)
    p.add_argument("--storage-price-gb-month", type=float, help="storage price per GB-month from RunPod's pricing page")
    p.add_argument("--json", action="store_true")
    p = sub.add_parser("endpoint", help="serverless endpoint request (dry run unless --execute)")
    p.add_argument("--endpoint-id", required=True)
    p.add_argument("--operation", choices=tuple(OPERATIONS), required=True)
    p.add_argument("--job-id")
    p.add_argument("--input", help="JSON object passed as the job input")
    p.add_argument("--execute", action="store_true", help="send the request (costs money; needs approval)")
    p.add_argument("--base-url", help="override the API base (for tests)")
    p.add_argument("--timeout", type=float, default=90)
    args = parser.parse_args(argv)
    try:
        if args.command == "vram":
            result = estimate_vram(args.params_b, args.precision, args.mode, args.context, args.batch, args.layers,
                                   args.kv_heads, args.head_dim, args.kv_precision, args.overhead)
            sizes = [float(s) for s in args.gpu_sizes.split(",") if s.strip()]
            result["recommendation"] = recommend_gpu(result["total_gib"], sizes)
            print(json.dumps(result, indent=2))
            return 0
        if args.command == "plan":
            plan = build_plan(args)
            if args.json:
                print(json.dumps(plan, indent=2))
            else:
                print("{} plan: {} x {} for {:.0f} GPU hours".format(plan["type"], plan["gpu_count"], plan["gpu"],
                                                                     plan["gpu_hours"]))
                print("compute {:.2f} + storage {:.2f} = {:.2f} (prices: {})".format(
                    plan["compute_cost"], plan["storage_cost"], plan["total_cost"], plan["price_source"] or "MISSING"))
                for item in plan["persistence_and_billing"]:
                    print("- " + item)
                print("Shutdown checklist:")
                for item in plan["shutdown_checklist"]:
                    print("  [ ] " + item)
                print(plan["approval_request"])
                for item in plan["errors"]:
                    print("error: " + item)
            return 0 if plan["ok"] else 1
        request = endpoint_request(args)
        if not args.execute:
            print(json.dumps(dict(request, dry_run=True, note="nothing was sent; add --execute after approval"), indent=2))
            return 0
        print(json.dumps(send(request, args.timeout), indent=2))
        return 0
    except RunPodError as exc:
        print("error: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
