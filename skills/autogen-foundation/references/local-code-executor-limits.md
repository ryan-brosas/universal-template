<!-- capsule-v2 -->
# Local command executor limits — how does a subprocess executor bound time and cancellation without leaking processes?

**Source:** autogen (MIT — LICENSE-CODE) `main@027ecf0a379bcc1d09956d46d12d44a3ad9cee14`; Codebase Memory project `autogen` (FULL, 16,432 nodes / 86,358 edges, generation 2026-08-24T16:12:29Z). **Question:** What exit-code vocabulary and kill choreography distinguish timeout, cancellation, and program failure?

## wait_for ladder: 124 = timeout, 125 = token-cancelled, nonzero = program failure, fail-fast across blocks
**Path/Symbol:** `python/packages/autogen-ext/src/autogen_ext/code_executors/local/__init__.py` `LocalCommandLineCodeExecutor._execute_code_dont_check_setup` :341–474 (`execute_code_blocks` :324–339 adds the setup-checked wrapper).
**Signature:** `async def _execute_code_dont_check_setup(self, code_blocks: List[CodeBlock], cancellation_token: CancellationToken) -> CommandLineCodeResult`.
**Data Shape:** `CodeBlock(language, code)`[] → `CommandLineCodeResult(exit_code: int, output: str, code_file: str | None)`; scripts written as `tmp_code_<sha256(code)>}.{ext}` in `work_dir`.

### Decisive source
```python
task = asyncio.create_task(asyncio.create_subprocess_exec(
    program, *extra_args, cwd=self.work_dir,
    stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE, env=env))
cancellation_token.link_future(task)          # token cancel kills process creation/wait
proc = await task
try:
    stdout, stderr = await asyncio.wait_for(proc.communicate(), self._timeout)
    exitcode = proc.returncode or 0
except asyncio.TimeoutError:
    logs_all += "\nTimeout"; exitcode = 124
    if proc: proc.terminate(); await proc.wait()   # fully dead before returning
    break
except asyncio.CancelledError:
    logs_all += "\nCancelled"; exitcode = 125
    if proc: proc.terminate(); await proc.wait()
    break
...
if exitcode != 0:
    break                                   # fail-fast: later blocks skipped
```

**Flow:** per block: silence pip output → normalize python variants → unknown language ⇒ `exitcode=1`, break → derive filename from content marker else sha256 hash → optional venv: prepend `bin_path` to PATH and invoke `env_exe` absolutely → subprocess task linked to the token → timed communicate → classify outcome → stop on first failure → concatenate logs → optionally unlink temp files (`missing_ok=True`).
**Invariant:** timeout (124) and cancellation (125) are DISTINCT exit codes from program failure; the child is always terminate()+wait()ed before returning — no zombie processes; a failing block prevents execution of subsequent blocks; unsupported languages fail with exit code 1 and an explanatory log rather than raising.
**Probe:** `python/packages/autogen-ext/tests/code_executors/test_commandline_code_executor.py::test_commandline_code_executor_timeout` (:171–177 — `time.sleep(10)` with `timeout=1` ⇒ truthy `exit_code` and `"Timeout" in output`). NOTE: this executor shells out on the HOST — it is NOT sandboxed; confinement is work_dir + optional venv only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "autogen", name_pattern: "execute_code|_execute_code|_run_code", file_pattern: "*code_executors/local*", limit: 12 });
```

## Verdict
Adopt the 124/125/nonzero exit-code taxonomy and terminate-and-await cleanup for any local subprocess runner. Adapt language invocation (`lang_to_cmd`, PowerShell flags) to your host. Omit the venv context if your platform manages environments externally — and do NOT port this as-is where untrusted code runs; use the docker/jupyter siblings instead.
