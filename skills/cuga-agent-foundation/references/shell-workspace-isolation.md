<!-- capsule-v2 -->
# Shell sandboxes — per-thread workspace isolation: uv-isolated venv, scrubbed env, and the virtual /workspace path contract

**Source:** cuga-agent Apache-2.0 `main@5de53ade`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** An agent runs shell commands on the host (or in a local Seatbelt sandbox) across concurrent threads. How do you isolate package installs, caches, and file visibility per thread WITHOUT Docker — and how does the agent see one stable `/workspace` root while the host layout varies by mode?

## The shell executor pair
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/executors/local/local_sandbox_executor.py` (`LocalSandboxExecutor._ensure_workspace_venv` :77-117, `_command_env` :119-139, `_run_command` :191-229); `native/native_sandbox_executor.py` (`_build_policy` :48-69, `_ensure_venv` :90+); `filesystem/paths.py` (`thread_workspace_root` :134, `resolve_workspace_path` :208+, `public_workspace_path` :259, `VIRTUAL_WORKSPACE_ROOT="/workspace"` :25).
**Signature:** `_run_command(cmd, *, thread_id=None, timeout=120) -> (stdout, stderr, returncode)`; `create_run_command_tool(thread_id) -> async run_command(cmd) -> str`.
**Data Shape:** workspace = `<cwd>/cuga_workspace/` shared when skills off, `cuga_workspace/<safe_thread_id>/` per-thread when on; agent-visible root is ALWAYS `/workspace`.

### Decisive source
```python
# local_sandbox_executor.py:119-138 — every cache/write location redirected into the thread
env["UV_NO_CONFIG"] = "1"          # uv must not discover the Cuga repo's pyproject
env["HOME"] = wr; env["TMPDIR"] = wr
env["VIRTUAL_ENV"] = str(venv.resolve())
env["XDG_CACHE_HOME"]   = .../.cache; env["UV_CACHE_DIR"] = .../.uv-cache
env["NPM_CONFIG_CACHE"] = .../.npm;  env["npm_config_prefix"] = wr
env["PATH"] = venv_bindir + os.pathsep + env.get("PATH", "")

# native_sandbox_executor.py:53-66 — Seatbelt: reads broad, writes confined
"(allow file-read*)\n"
"(allow file-write*\n    (subpath \"/private/tmp\")\n"
f"    (subpath \"{workspace_parent}\")\n    (literal \"/dev/null\")\n)\n"
```

**Flow:** ensure `<workspace>/.venv` (uv first — `UV_NO_CONFIG=1`, never merging packages into the host repo's lockfile — then `python -m venv` fallback) → build the env above → run `/bin/sh -c "cd <workspace> && <cmd>"` with piped stdout/stderr under `wait_for(timeout)` (timeout kills the process) → non-zero return code appends `(exit code N)` to stderr → tool formats via `format_run_command_output(stdout, stderr, failed=rc!=0)` (stderr only on failure; empty output becomes "(command completed with no output)"). Native mode wraps the same flow in `sandbox-exec` with a generated policy whose write surface is exactly /private/tmp + the workspace tree. Path translation both ways: `resolve_workspace_path` maps `/workspace/...` or `./uploads/...` onto the thread root (rejecting traversal), `public_workspace_path` renders host paths back to `/workspace/...`.
**Invariant:** the readiness flag for the native venv checks the activate SCRIPT's presence, not directory existence — a stale crashed `/tmp/.venv` without `bin/activate` is wiped and recreated rather than freezing the executor broken for the process lifetime. Host-side isolation is ENV-scrubbing plus cwd confinement, not a security boundary: the docstring mandates pairing `run_command` with a ToolApproval policy.

**Probe:** direct tests `tests/unit/test_workspace_sandbox.py::test_native_workspace_file_access_maps_workspace_to_thread_root` (:241), `::test_native_workspace_file_access_rejects_paths_outside_public_workspace` (:271), `::test_fetch_native_workspace_tree_is_per_thread_and_public_workspace` (:208); `tests/unit/test_sandbox_uv_guidance.py::test_sandbox_uv_guidance_forbids_bare_uv_run` (:5); `executors/tests/test_local_sandbox_skills.py` (skills copy).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "LocalSandboxExecutor _command_env thread_workspace_root resolve_workspace_path VIRTUAL_WORKSPACE_ROOT", limit: 10 });
```

## Verdict
Adopt per-thread workspace roots with fully redirected HOME/TMPDIR/caches and an isolated venv, the stable virtual `/workspace` contract over mode-dependent host layouts, and readiness flags keyed to real artifacts (activate script), not directories. Adapt the workspace dirname, venv tooling, and (on macOS) Seatbelt write-paths to your host. Omit the skills-copy step unless you run skill flows.
