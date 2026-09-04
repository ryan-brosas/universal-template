<!-- capsule-v2 -->
# TTY-forked shell runner — interactive pexpect passthrough vs char-streamed subprocess capture

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider` (full index). **Question:** How does a coding agent run model-suggested shell commands so interactive programs still work when a human is watching, yet output is always captured for chat?

## Dispatch on interactivity, never raise
**Path/Symbol:** `aider/run_cmd.py`: `run_cmd(command, verbose=False, error_print=None, cwd=None)` (:11), `run_cmd_subprocess(...)` (:42), `run_cmd_pexpect(...)` (:89), `get_windows_parent_process_name()` (:26).
**Signature:** all return `(exit_status: int, combined_output: str)`; OSError at the top dispatcher converts to `(1, error_message)` — the function NEVER raises.
**Data Shape:** dispatch predicate = `sys.stdin.isatty() and hasattr(pexpect, "spawn") and platform.system() != "Windows"`; subprocess mode merges stderr into stdout and echoes byte-by-byte (`read(1)` + `print(..., flush=True)`) so the human watches progress live while the string accumulates.

### Decisive source
```python
try:
    if sys.stdin.isatty() and hasattr(pexpect, "spawn") and platform.system() != "Windows":
        return run_cmd_pexpect(command, verbose, cwd)
    return run_cmd_subprocess(command, verbose, cwd)
except OSError as e:
    error_message = f"Error occurred while running command '{command}': {str(e)}"
    ...
    return 1, error_message
```
Interactive branch hands the terminal to the child (`child.interact(output_filter=output_callback)` tapping every byte into a BytesIO) using `$SHELL -i -c <command>`; Windows PowerShell parents get their command re-wrapped as `powershell -Command ...` in subprocess mode.

**Flow:** pick transport by TTY/platform → stream/echo output → wait → return code+output; every failure path inside the transports also degrades to `(1, message)` rather than raising.
**Invariant:** output is ALWAYS captured regardless of transport; exit status always an int; interactive control transfer only when a real terminal exists (headless hosts silently get the subprocess path).
**Probe:** `tests/basic/test_run_cmd.py::test_run_cmd_echo` (:6) pins the echo path; executed this run: `.pi/work/foundations-deep-farm/scratch-aider-pass2/probe_gate5.py::run-cmd-subprocess` (rc=0 with streamed capture under repo venv).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", name_pattern: "run_cmd_subprocess", limit: 5 });
// also resolves: run_cmd_pexpect, get_windows_parent_process_name
```

## Verdict
Adopt the never-raise tuple contract + TTY-gated interactive escalation; adapt the PowerShell wrapper and shell selection; omit nothing else. Direct test covers only the trivial echo case — streaming behavior additionally probe-pinned this run.
