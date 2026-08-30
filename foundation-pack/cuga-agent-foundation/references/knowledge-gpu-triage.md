<!-- capsule-v2 -->
# GPU-transparency triage — how do you turn "GPU missing" into three distinct operator-remediation messages instead of one misleading warning?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** What are the distinct GPU failure modes at engine startup and which combination must become a fatal error?

## Three-case diagnosis: (a) no device visible, (b) CPU-only image, (c) partial GPU
**Path/Symbol:** `src/cuga/backend/knowledge/engine.py:1855-1928` (`KnowledgeEngine.__init__` GPU block), `:817-864` (`_detect_accelerator`).
**Signature:** `_detect_accelerator(use_gpu: bool) -> tuple[str, list[str]]` (device label + ONNX providers); diagnostics inline in `__init__`.
**Data Shape:** Inputs: `config.use_gpu`, providers list, `torch.cuda.is_available()`, env `CUGA_GPU_BUILD=1`, `CUGA_GPU_REQUIRED=1` (or `config.gpu_required`). Output: one of three messages, a worker-count nudge, or silence.

### Decisive source
```python
# engine.py:1860-1865 — why the split exists
# A single-line warning conflated three very different failure modes —
# operators read it and pick the wrong remediation.
only_cpu_onnx = _providers == ["CPUExecutionProvider"]
try:
    import torch; _torch_cuda = torch.cuda.is_available()
except Exception:
    _torch_cuda = False
# (a) only_cpu_onnx and not _torch_cuda and CUGA_GPU_BUILD=1  → "pass --gpus all / add nvidia.com/gpu limit"
# (b) only_cpu_onnx and not _torch_cuda (no build flag)        → "run the GPU image or uv sync --extra gpu"
# (c) only_cpu_onnx and _torch_cuda                            → "partial: reranker+Docling get CUDA, embedder stays CPU — add onnxruntime-gpu"
```
Case (c) is the sneaky one: torch sees CUDA so the operator believes GPU is engaged, but fastembed/ONNX keeps running on CPU — remediation is adding the GPU runtime package, NOT rebuilding the image. When `gpu_required=True` (config or env), ANY of the three cases raises `RuntimeError("[cuga] gpu_required=True but GPU runtime is not loaded. " + msg)` — vLLM/TGI-style fail-fast for operators who never want silent CPU regressions. Bonus sizing nudge: CUDA fully wired but `max_ingest_workers <= 2` ⇒ warn that an H100 fits ~8–14 Docling workers (kept as warning, not error — small-GPU operators may have chosen it deliberately).

**Flow:** init → detect providers + torch CUDA → classify (a)/(b)/(c) → msg built with case-specific fix instructions → gpu_required ? raise : warn → optional ingest-worker sizing hint.
**Invariant:** Never collapse infrastructure failure modes into one message when their fixes differ; silent CPU degradation must be opt-outable via an explicit required-GPU flag.

**Probe:** No dedicated unit test in tests/unit — coverage caveat: environment-dependent behavior verified by reading source + `_detect_accelerator` logic; port with your own container matrix.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "gpu_required detect_accelerator CPUExecutionProvider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-case classification with per-case remediation text and the fail-fast escape hatch. Adapt flags/env names to your deployment. Omit the worker-count nudge if you have no GPU ingest path.
