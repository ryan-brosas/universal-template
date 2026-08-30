<!-- capsule-v2 -->
# Dual memory limits — why must you set BOTH the Docker limit and v8's max-old-space?

**Source:** nodebestpractices CC-BY-SA-4.0 `master@dc3d60c29d5483d9ea99cf261bbd6203516a2ba7`; Codebase Memory `nodebestpractices`. **Question:** What happens if you set only one of the two memory limits, and how do the two relate?

## Docker decides placement; v8 decides GC timing
**Path/Symbol:** `sections/docker/memory-limit.md` (explainer :7, docker run :11-14, K8s+v8 :16-27).
**Signature:** Docker: `docker run --memory 512m my-node-app` or K8s `resources.requests/limits.memory`. v8: `node index.js --max-old-space-size=350`. The v8 value should be ~75-100% of the container limit.
**Data Shape:** Docker limit alone → runtime knows how to scale/place and when to crash a burst, but JS GC won't fire early → process crashes at ~50-60% of host resources. v8 limit alone → GC fires correctly but the orchestrator can't place the container or protect neighbors.

### Decisive source
```yaml
# memory-limit.md :16-27 — the pair
spec:
  containers:
  - name: my-node-app
    resources:
      requests: { memory: "400Mi" }
      limits:   { memory: "500Mi" }
    command: ["node index.js --max-old-space-size=350"]
```
Explainer (:7): "Without setting v8's --max-old-space-size, the JavaScript runtime won't push the garbage collection when getting close to the limits and will also crash when utilizing only 50-60% of the host environment. Consequently, set v8's limit to be 75-100% of Docker's memory limit."

**Flow:** container requests/limits at the orchestrator → v8 flag set just under the limit → as memory approaches the v8 cap, GC runs to free space (Node docs: "V8 will spend more time on garbage collection…") → only genuine overflow hits the Docker limit → OOMKill is the last resort, not the norm.
**Invariant:** both layers are required; they serve different purposes (placement/health vs GC/under-utilization). Setting v8's limit to a value much larger than the container limit defeats the GC early-warning; much smaller wastes headroom.
**Probe:** no runner upstream. Deterministic probe: `grep -c 'max-old-space-size' sections/docker/memory-limit.md` ≥ 2 (explainer + command).

## Get live surrounding code
**Retrieve:**
**Retrieve:** doc-shaped/BM25-gap note — `search_graph` text queries return ZERO on this graph (Section nodes carry no searchable tokens); use `search_code`, executed live:
```bash
codebase-memory-mcp cli search_code '{"project": "nodebestpractices", "pattern": "max-old-space-size", "limit": 10}'
# resolves `sections/docker/memory-limit.md` line-exact (verified 2026-08-24)
```

## Verdict
Adopt the dual-limit pair for any managed-runtime container. Adapt the v8 ratio and orchestrator syntax per platform. Omit nothing — the two-layer reasoning is the contract.
