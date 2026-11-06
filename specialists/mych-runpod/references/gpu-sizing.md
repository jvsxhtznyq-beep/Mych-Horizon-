# GPU and VRAM Sizing

Estimating memory before renting a GPU, and checking the estimate after.

## Inference

```text
weights  = parameters x bytes per parameter
KV cache = 2 x layers x KV heads x head dimension x context tokens x batch x bytes per KV value
total    = (weights + KV cache) x (1 + overhead)
```

| Precision | Bytes per parameter |
|---|---|
| fp32 | 4 |
| fp16, bf16 | 2 |
| fp8, int8 | 1 |
| int4 | 0.5 |

- Read layers, KV heads (grouped-query attention models have fewer KV heads than attention heads) and head dimension from the model's configuration file.
- The KV cache grows linearly with context length and batch size and often dominates at long contexts.
- The overhead allowance (20 percent by default in `runpod_tool.py vram`) covers runtime buffers and fragmentation; serving frameworks may reserve more memory up front.

Example: an 8-billion-parameter model in fp16 with 32 layers, 8 KV heads, head dimension 128 and an 8,192-token context needs about 14.9 GiB of weights plus 1.0 GiB of KV cache, about 19 GiB with overhead: a 24 GB GPU fits one sequence at that context.

## Training

- Full fine-tuning with mixed-precision Adam needs roughly 16 bytes per parameter (weights, gradients, optimizer states) before activations, so large models need several GPUs.
- LoRA keeps the base model frozen (at its precision) and trains small adapters; memory is close to inference plus activations.
- Activation memory depends on batch size, sequence length and checkpointing; measure it.

## Verify

Estimates are a starting point. Run a short test on the chosen GPU, watch peak memory with the framework's tools or `nvidia-smi`, and adjust batch size, context or precision before committing to long runs.
