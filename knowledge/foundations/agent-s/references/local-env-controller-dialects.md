<!-- capsule-v2 -->
# local-env-controller-dialects — What does the minimal local execution backend look like, and what are its sharp edges?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How do LocalController/LocalEnv satisfy the CodeAgent's controller interface, and what differs from the OSWorld remote controller?

## Local env seam
**Path/Symbol:** `gui_agents/s3/utils/local_env.py:LocalController` (:6-70) + `LocalEnv` (:73-77); opt-in at `gui_agents/s3/cli_app.py` (`--enable_local_env`, :312-317, LocalEnv() :352-357).
**Signature:** `run_bash_script(code, timeout=30) -> Dict`; `run_python_script(code) -> Dict`; `LocalEnv().controller` is the only attribute CodeAgent needs.
**Data Shape:** bash: `/bin/bash -lc code` with capture + 30s timeout; python: `sys.executable -c code` (no timeout). Both return the dialect dicts consumed by format_result (see bash-python-result-dialects capsule).

### Decisive source
```python
class LocalController:
    """Minimal controller to execute bash and python code locally.

    WARNING: Executing arbitrary code is dangerous. Only enable/use this in trusted
    environments and with trusted inputs.
    """
    def run_bash_script(self, code: str, timeout: int = 30) -> Dict:
        proc = subprocess.run(["/bash", "-lc", code], capture_output=True, text=True, timeout=timeout)
        output = (proc.stdout or "") + (proc.stderr or "")
        return {"status": "ok" if proc.returncode == 0 else "error", "returncode": proc.returncode,
                "output": output, "error": ""}

# cli_app.py — explicit opt-in with warning
parser.add_argument("--enable_local_env", action="store_true", default=False,
    help="Enable local coding environment for code execution (WARNING: Executes arbitrary code locally)")
```

**Flow:** CLI flag ⇒ LocalEnv() replaces the default env=None → OSWorldACI carries it → call_code_agent requires `env.controller` non-None else the action vanishes from the worker's API (worker reset skip list) → CodeAgent executes each step through run_*_script on the HOST machine.
**Invariant:** (1) The controller duck-type is just two methods — any sandbox (docker, VM, remote) satisfying them slots in; OSWorld's real controller lives outside this repo. (2) bash merges stderr into stdout (terminal-like view); python keeps them separate — matching the formatter dialects. (3) Python has NO timeout: an infinite loop in a generated step hangs the whole agent. (4) Default OFF with double warning (flag help + runtime print) because execution lands on the user's own machine. (5) TimeoutExpired preserves partial stdout with returncode -1.
**Probe:** `grep -n '/bin/bash", "-lc"' gui_agents/s3/utils/local_env.py` → :16.
**Probe:** `grep -n 'enable_local_env' gui_agents/s3/cli_app.py` → :313 (arg) and :353 (gate).
**Probe:** `grep -n 'timeout=timeout' gui_agents/s3/utils/local_env.py` → :20 (bash only).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "LocalController run_bash_script LocalEnv enable_local_env", limit: 5 });
```

## Verdict
Adopt the two-method controller duck type as the sandbox seam for code agents; adapt backends freely; omit nothing structurally but FIX the missing python timeout deliberately when porting to untrusted settings.
