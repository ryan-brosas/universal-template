<!-- capsule-v2 -->
# Sanitized subprocess env — why must HOME/TMPDIR point INTO the sandbox and OUTPUT_DIR be exported?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** What exact environment does an untrusted-code subprocess need so host secrets never leak in and tool cache/config writes stay inside the confined scope?

## Allowlist-only env, not a denylist strip
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/environment.py:sanitized_subprocess_env` (L44–73); `EnvironmentManager._run_confined` (L215–229).
**Signature:** `sanitized_subprocess_env(working_dir: str) -> dict[str, str]`.
**Data Shape:** Exactly `{PATH (host), HOME=working_dir, TMPDIR=working_dir, LANG, OUTPUT_DIR=working_dir/output}` (+ 5 Windows npm keys when present). Nothing else crosses.

### Decisive source
```python
env = {
    "PATH": host_path,
    "HOME": working_dir,     # npm/pip config+cache land INSIDE the sandbox dir,
    "TMPDIR": working_dir,   # within the confined write scope — not ~/.npm etc.
    "LANG": os.environ.get("LANG", "en_US.UTF-8"),
    # parity with the Docker backend's env={"OUTPUT_DIR": "/output"}:
    # "write it to $OUTPUT_DIR" is ONE contract that holds on either backend.
    "OUTPUT_DIR": os.path.join(working_dir, "output"),
}
```

**Flow:** `EnvironmentManager.install_packages` → validate specs → ensure runtime/venv lazily → `_run_confined`: wrap argv with `confine_command(cmd, working_dir, allow_network=self._allow_network_on_install)` → spawn with the sanitized env → decode with `errors="replace"` → `ExecResult`. The SAME sanitizer is applied by `CodeExecutor._run` for execution (network denied there by default).
**Invariant:** (1) Allowlist construction, NOT stripping a copied environ — any secret added to the parent env later (API keys, cloud tokens) can't leak by omission of a deny rule. (2) HOME/TMPDIR redirection is what makes kernel-confinement write-scoping sufficient for tools that insist on writing dotfiles/cache. (3) `$OUTPUT_DIR` semantics are identical across local/docker backends; porters who drop it break the documented artifact convention silently. (4) Installs run under the same confinement as execution; only the network flag differs.
**Probe:** `tests/unit/agent_loop_lib/sandbox/test_local_coding_sandbox.py::test_output_dir_is_working_dir_slash_output` (:22) pins `env["OUTPUT_DIR"] == f"{working_dir}/output"`; confinement + spec-validation behavior pinned via `test_docker_coding_sandbox.py:451–491` and `test_validation.py` (see package-spec capsule).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "sanitized_subprocess_env EnvironmentManager _run_confined confine_command", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt allowlist-env + HOME/TMPDIR redirection + explicit OUTPUT_DIR export verbatim for any confined-subprocess runner; adapt the Windows key set to host requirements. Omit PipesHub's venv/npm layout choices if the host has its own. Direct test coverage thin here (one env assertion) — behavior largely pinned indirectly through executor/sandbox suites; recorded as caveat, not overstated.
