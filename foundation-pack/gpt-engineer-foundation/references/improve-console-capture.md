<!-- capsule-v2 -->
# improve-console-capture — How is a crashing interactive improve run debugged post-mortem?

**Source:** gpt-engineer MIT `main@a90fcd54`; Codebase Memory `gpt-engineer`. **Question:** What wraps handle_improve_mode so failures still yield a debug artifact?

## Console capture seam
**Path/Symbol:** `gpt_engineer/core/default/steps.py:Tee` (:363-373) + `handle_improve_mode` (:376-397).
**Signature:** `handle_improve_mode(prompt, agent, memory, files_dict, diff_timeout=3) -> Optional[FilesDict]`.
**Data Shape:** stdout duplicated live+captured; capture flushed into DEBUG_LOG_FILE (`debug_log_file.txt`) appended after prior sections ("UPLOADED FILES:", "PROMPT:", "CONSOLE OUTPUT:").

### Decisive source
```python
captured_output = io.StringIO()
old_stdout = sys.stdout
sys.stdout = Tee(sys.stdout, captured_output)
try:
    files_dict = agent.improve(files_dict, prompt, diff_timeout=diff_timeout)
except Exception as e:
    print(f"Error while improving the project: {e}\nCould you please upload the debug_log_file.txt in {memory.path}/logs folder to github?\nFULL STACK TRACE:\n")
    traceback.print_exc(file=sys.stdout)
finally:
    sys.stdout = old_stdout
    captured_string = captured_output.getvalue()
    print(captured_string)
    memory.log(DEBUG_LOG_FILE, "\nCONSOLE OUTPUT:\n" + captured_string)
return files_dict
```

**Flow:** Tee stdout → attempt improve → ANY exception prints apology + full traceback INTO THE TEE (so it lands in the log) → finally restores stdout, replays capture to console, appends CONSOLE OUTPUT section to debug log → returns possibly-None/partial files_dict.
**Invariant:** (1) Exception SWALLOWED: caller distinguishes failure by falsy/unchanged files_dict (`if not files_dict or files_dict_before == files_dict`) — no exception propagates past this boundary. (2) Tee restores stdout in finally even mid-crash — leak-free global mutation. (3) The debug log accumulates sections across attempts (uploaded files → prompt → console output) making one file sufficient for a GitHub issue. (4) traceback.print_exc(file=sys.stdout) targets the TEE, not stderr — deliberate so traces persist.
**Probe:** `grep -n 'traceback.print_exc(file=sys.stdout)' gpt_engineer/core/default/steps.py` → :387.
**Probe:** `grep -n 'class Tee' gpt_engineer/core/default/steps.py` → :363.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "gpt-engineer", query: "handle_improve_mode Tee captured_output DEBUG_LOG_FILE", limit: 10 });
```

## Verdict
Adopt tee-and-swallow with sectioned debug log for long-running interactive agents; adapt to logging framework equivalents; keep the unchanged-files failure signal contract between this and main.py.
