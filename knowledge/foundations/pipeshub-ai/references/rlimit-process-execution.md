<!-- capsule-v2 -->
# Rlimit process execution — what bounds confinement does NOT provide (CPU/memory/fork bombs)?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** Kernel confinement scopes files/network but caps no resources — how does the executor stop `while(true){}` and fork bombs?

## setrlimit preexec + whole-process-group kill on timeout
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/executor.py:ExecutionLimits/_rlimit_preexec_fn/_kill_process_tree/CodeExecutor._run` (L59–240); artifact snapshot `_snapshot_mtimes` (L82–98).
**Signature:** `CodeExecutor.execute(CodeRequest) -> CodeResult` (error_analysis left None — ReflectionEngine's job); `ExecutionLimits(max_memory_bytes=1.5GiB, max_cpu_seconds=30, max_file_size_bytes=50MiB, max_processes=2048)`.
**Data Shape:** POSIX-only rlimits via lazy `import resource` in a preexec fn; `start_new_session=True` so the child leads its own process group; Windows degrades to timeout-kill only (documented).

### Decisive source
```python
def _preexec():
    for res, value in (
        (resource.RLIMIT_AS,   limits.max_memory_bytes),
        (resource.RLIMIT_CPU,  limits.max_cpu_seconds),
        (resource.RLIMIT_FSIZE, limits.max_file_size_bytes),
        (resource.RLIMIT_NPROC, limits.max_processes),
    ):
        try: resource.setrlimit(res, (value, value))
        except (ValueError, OSError): continue  # best-effort in containers/CI

async def _kill_process_tree(proc):
    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)   # GROUP, not proc — a
    ...                                                # fork-bombing/backgrounding
                                                       # script must not survive

# ExecutionLimits docstring caveat: on macOS/BSD RLIMIT_NPROC limits processes
# owned by the REAL UID system-wide, not this subtree — default 2048 is
# deliberately generous so ordinary desktops never hit confusing EAGAIN.
```

**Flow:** ensure runtime/venv BEFORE the artifact snapshot (bootstrap ≠ agent output) → write entry → tsc `--noEmit` pre-pass for TS (`bundler` module resolution — tsx strips types without checking, and without this pass no TYPE category could ever fire) → confined+rlimited spawn with sanitized env → `wait_for(communicate(), timeout)` → timeout ⇒ SIGKILL the group → artifacts = mtime diff excluding entry file.
**Invariant:** (1) Confinement and rlimits are ORTHOGONAL layers — Seatbelt/bwrap say WHERE you may write; rlimits say HOW MUCH you may consume; skipping either leaves a real hole. (2) Kill must target the process GROUP or backgrounded children outlive the timeout. (3) Bootstrap runs before the before-snapshot or npm/venv creation misreports as thousands of artifacts. (4) rlimit application is per-value best-effort — some are unavailable under containers/CI and must not abort the run.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_executor.py::test_entry_file_itself_is_not_reported_as_an_artifact` (:27), `::test_real_output_file_is_still_reported_as_an_artifact` (:38), `::test_custom_entry_file_is_also_excluded` (:49).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "ExecutionLimits _rlimit_preexec_fn _kill_process_tree CodeExecutor", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-layer model (confinement × rlimits), process-group kill, and bootstrap-before-snapshot ordering; adapt limit VALUES to host (keep the NPROC-system-wide caveat in your docs). Omit PipesHub's tsc flag choices only if you don't type-check TS. Direct tests cover artifact-diff edges; rlimits themselves are POSIX-standard behavior (no test claims).
