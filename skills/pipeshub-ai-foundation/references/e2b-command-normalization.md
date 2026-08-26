<!-- capsule-v2 -->
# E2B commands.run contract — how does a remote micro-VM backend keep the errors-as-data + filesystem-only contracts?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What must a remote backend normalize so swapping it in for the local backend never changes observable behavior?

## CommandExitException → tuple normalization; run_code() forbidden
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/e2b.py:E2BCodingSandbox._run_command` (L267–283); class docstring (L26–48); `_ensure_typescript_runtime` (L249–258).
**Signature:** `_run_command(cmd: str, *, timeout: float) -> (stdout, stderr, exit_code)` — the ONLY sanctioned execution primitive.
**Data Shape:** Server-assigned `sandbox_id` (raises if read pre-provision, vs local's __init__ uuid); fixed `_WORKING_DIR = /home/user` (whole VM already single-tenant); artifacts via whole-listing set difference.

### Decisive source
```python
# E2B's run() RAISES CommandExitException on non-zero exit instead of
# returning a result with exit_code != 0 — normalized here into data:
try:
    result = await self._sbx.commands.run(cmd, cwd=_WORKING_DIR, timeout=timeout)
    return result.stdout, result.stderr, result.exit_code
except CommandExitException as e:
    return e.stdout, e.stderr, e.exit_code          # code-level failure = DATA
except TimeoutException as e:
    return "", str(e) or "Execution timed out", -1  # matches -1 timeout shape

# Deliberately uses commands.run() (process-per-execution), NEVER E2B's
# run_code() stateful Jupyter-kernel API — using it would let interpreter
# state leak across calls, silently changing behavior when an agent swaps
# from backend="local" to backend="e2b" (a Liskov substitution violation).

# TypeScript runs the INSTALLED binary, not npx:
"typescript": "./node_modules/.bin/tsx {file}",
# npx would try to resolve against its registry/cache first and can attempt
# a network fetch even when the package is already installed locally.
```

**Flow:** lazy `provision()` (`AsyncSandbox.create`) → optional package install (same validation/allowlist/denylist/idempotency semantics as `EnvironmentManager`, over `commands.run`) → first TS use: `npm init -y` + install `tsx typescript` ONCE (`_node_initialized` latch) → write entry via `files.write` → snapshot file listing → run → artifacts = `sorted(after - before - {entry_file})` → failures get `ReflectionEngine.analyze` like every backend.
**Invariant:** (1) Only infrastructure failures raise; code-level non-zero exits come back as `(stdout, stderr, exit_code)` data — a provider whose SDK raises on exit codes must be wrapped or it breaks the ABC. (2) No stateful interpreter API may leak through this interface (filesystem-only persistence is THE interchangeability contract). (3) TS runtime bootstrap is one-time and explicit — never an implicit network fetch at execution time. (4) Traversal guard uses posixpath against the VM path root, mirroring local/docker `_resolve_path`.
**Probe:** No direct unit test at HEAD (`E2BCodingSandbox` appears in no tests/ file) — coverage caveat recorded; deterministic probes are source-symbol greps + `search_graph` retrieval of `E2BCodingSandbox._run_command`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "E2BCodingSandbox _run_command CommandExitException AsyncSandbox.create", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exception→data normalization at the transport boundary and the no-stateful-API rule for ANY remote sandbox adapter; adapt working dir, template, timeouts. Coverage caveat stands until upstream ships an e2b suite — do not claim test-backed behavior for this capsule beyond the sibling backends' shared-contract tests.
