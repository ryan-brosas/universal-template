<!-- capsule-v2 -->
# Coding-sandbox lifecycle — how are untrusted-code sandboxes created, bounded, and torn down without leaks?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What does the backend ABC contract and its manager have to guarantee so local/docker/e2b backends are interchangeable and nothing outlives its budget?

## Errors-as-data runs + capability-shared manager records
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/base.py:CodingSandboxBackend/CodeResult` (L134–260); `backend/python/app/agent_loop_lib/sandbox/manager.py:SandboxManager` (L80–219); `backend/python/app/agent_loop_lib/sandbox/coding/base.py:normalize_sandbox_path` (L56–77).
**Signature:** `execute(CodeRequest) -> CodeResult` (never raises for code-level failure); `get_or_create(type, sandbox_id=None) -> tuple[str, Any]`.

```python
# base.py — the error-propagation contract (CodeResult docstring):
# "a failed run (nonzero exit, exception, timeout) is represented HERE —
#  exit_code non-zero and error_analysis populated — not as a raised
#  exception. ... Only infrastructure failures (missing runtime, unknown
#  sandbox, sandbox destroyed mid-call) should raise."
#
# State contract (CodingSandboxBackend docstring): "only the FILESYSTEM
# persists between execute() calls on the same instance — interpreter state
# does NOT. ... backends that offer richer semantics (e.g. E2B's stateful
# Jupyter-style contexts) must not expose them through this interface, so
# swapping backends never silently changes behavior (Liskov substitution)."

# manager.py — multi-capability tracking:
record = _InstanceRecord(backend=..., created_at=..., last_used_at=...)
for t in entry.capabilities:          # ONE factory can serve several types
    self._instances[(t, new_id)] = record   # same record under each key
# destroy() drops ALL keys of that record so a sibling type can't resolve
# an already-destroyed backend; destroy_all()/destroy() swallow teardown
# errors (log+continue) so one broken backend can't block shutdown.
```

**Data Shape:** `CodeRequest{code, language: ts|py, timeout=30, packages[], allow_network=False, entry_file}`; `CodeResult{stdout, stderr, exit_code, language, duration_ms, error_analysis?, artifacts[]}` with `.success == (exit_code==0)`; `ErrorAnalysis{category: syntax|type|runtime|import|timeout|permission|unknown, message, file?, line?, suggestion?, is_retryable}` is what makes reflection/self-correction possible without the model re-parsing stacks. `normalize_sandbox_path` rewrites ONLY `$OUTPUT_DIR`, `${OUTPUT_DIR}`, `/output` aliases to sandbox-relative `output/...` — every other absolute path stays absolute so `_resolve_path` still rejects escapes.

### Decisive source
```python
# manager.py get_or_create: existing id ⇒ refresh last_used_at and return;
# new ⇒ sweep_stale(max_lifetime) → check_concurrency(max_concurrent,
# raises SandboxLimitExceeded) → factory() → await provision() → read
# backend.sandbox_id AFTER provision (e2b only gets its id there; local
# generates in __init__ — the ABC documents both styles as legal).
```

**Flow:** ControlPlane registers a per-backend factory closure (fresh uuid working dir `alcs-<hex>` per instance) + `SandboxLimits(max_concurrent, max_lifetime_s)` → tool asks `get_or_create(CODING)` → lazy stale sweep enforces lifetime WITHOUT a background task → execute → artifacts detected by before/after mtime diff excluding entry file and dependency dirs (`node_modules/.venv/__pycache__/.git/.npm/node-compile-cache/tsx-*`) → `ControlPlane.stop()` ⇒ `sandbox_manager.destroy_all()`.

**Invariant:** (1) code failures are DATA, infra failures are EXCEPTIONS — collapsing this distinction turns retryable model mistakes into crashes or hides real breakage as fake successes. (2) The filesystem-only persistence guarantee is the interchangeability contract; a backend exposing richer state through this ABC breaks Liskov substitution for every consumer. (3) Concurrency/lifetime limits live in the MANAGER because they need live-count state middleware doesn't have. (4) Path aliasing must be allowlist-exact — blind prefix rewriting would let absolute paths be silently reinterpreted instead of rejected.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_docker_coding_sandbox.py:381/:398/:412` (nonzero exit populates error_analysis; infra exception NEVER raises; timeout kills container), `:188/:219` (second call reports only ITS new output), `:321-380` (default no-network; backend flag VETOES request allow_network both directions), `:451-491` (shell-metachar rejection; allow/denylist), `tests/unit/agent_loop_lib/sandbox/test_local_coding_sandbox.py:55/:66/:74` (all OUTPUT_DIR spellings resolve to one path; other paths untouched; escapes rejected), `test_executor.py:27/:38/:49` (entry file never an artifact; real outputs always).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "SandboxManager get_or_create CodeResult normalize_sandbox_path", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt errors-as-data + filesystem-only contracts, manager-owned limits with lazy sweeps, multi-capability record aliasing, and the mtime artifact diff. Adapt rlimit values (`ExecutionLimits`: 1.5GiB/30s CPU/50MiB files/2048 procs — note macOS RLIMIT_NPROC is system-wide for the real UID) and docker/e2b flags to host. Omit PipesHub's platform bridge (`app/agents/agent_loop/sandbox_bridge.py`) — pass-3 target tying this library to its artifact registry. Direct tests read at HEAD across three test files (~40 cases).
