<!-- capsule-v2 -->
# bash-python-result-dialects — Why does the result formatter branch on key presence rather than code type?

**Source:** Agent-S MIT `main@bffdb59c`; Codebase Memory `ext-agent-s`. **Question:** How do the two execution backends' result shapes differ, and how is the difference normalized for the model?

## Result dialect seam
**Path/Symbol:** `gui_agents/s3/utils/local_env.py:LocalController.run_bash_script` (:13-46) / `run_python_script` (:48-70); normalization at `gui_agents/s3/agents/code_agent.py:format_result` (:52-87) + dispatch in `execute_code` (:32-49).
**Signature:** `run_bash_script(code, timeout=30) -> {status, returncode, output, error}` vs `run_python_script(code) -> {status, return_code, output, error}`.
**Data Shape:** Bash merges stdout+stderr into ONE `output` string (stderr always ""); Python keeps stdout and stderr separate. The key NAME also differs: bash `returncode`, python `return_code`.

### Decisive source
```python
# format_result — dialect detected by KEY PRESENCE
return_code = result.get("returncode", result.get("return_code", -1))
if "returncode" in result:
    # Bash script response
    output = result.get("output", "")   # stdout AND stderr merged
    error = result.get("error", "")     # always empty for bash
else:
    # Python script response
    output = result.get("output", "")   # stdout only
    error = result.get("error", "")     # stderr only
```

**Flow:** extract_code_block picks python|bash by fence tag → execute_code dispatches to the controller method → raw dict flows back → format_result renders `Step N Result / Status / Return Code / Output? / Error?` text that becomes the next user message in the code agent's transcript. Missing result ⇒ synthetic "No result returned from execution" error block.
**Invariant:** (1) The formatter NEVER receives code_type — dialect detection rides on `returncode` presence, so any new backend must either match a dialect exactly or extend the formatter; silently reusing the bash key with split streams would misrender. (2) status is `"ok"` iff returncode==0 else `"error"`. (3) TimeoutExpired becomes `{status: error, returncode: -1, error: "TimeoutExpired: ..."}` preserving partial stdout. (4) Unknown fence types yield `{"status": "error", "error": f"Unknown code type: ..."}` without executing anything.
**Probe:** `grep -n 'result.get("returncode"' gui_agents/s3/agents/code_agent.py` → :62.
**Probe:** `grep -n '"returncode"' gui_agents/s3/utils/local_env.py` → :29/:36/:43 (bash arm); `grep -n '"return_code"' gui_agents/s3/utils/local_env.py` → :60/:67 (python arm).
**Probe:** `grep -n 'output = (proc.stdout or "") + (proc.stderr or "")' gui_agents/s3/utils/local_env.py` → :21.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-agent-s", query: "LocalController run_bash_script run_python_script format_result", limit: 5 });
```

## Verdict
Adopt explicit per-backend result dialects normalized at one formatting seam; adapt to your own controller shapes but keep dialect detection total (every backend maps to exactly one arm); omit nothing — merging stderr into stdout for shell is deliberate so the model sees interleaved output as a terminal would.
