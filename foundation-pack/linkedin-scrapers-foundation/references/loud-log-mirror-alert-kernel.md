<!-- capsule-v2 -->
# Loud log-mirror alert kernel — how do I mirror console output to a file and fail LOUDLY — but non-recursively — when the log target dies?

**Source:** Auto_job_applier_linkedIn MIT `main@0ca5550f8aa80027621cfc17a30fceba05705f84`; Codebase Memory `Auto_job_applier_linkedIn`. **Question:** every console line should also land in a persistent log, and a dead log target must be impossible to miss — without the failure handler itself recursing into alerts?

## print_lg dual write + blocking GUI alert with from_critical recursion guard
**Path/Symbol:** `modules/helpers.py:print_lg` (:126–139); `critical_error_log` (:104–108) sets `from_critical=True`; module init `__logs_file_path = get_log_path()` (:111–123, falls back to "./logs/log.txt"); production dir contract: `open_chrome.createChromeSession → make_directories([file_name, failed_file_name, logs_folder_path+"/screenshots", …])` (:32).
**Signature:** `print_lg(*msgs, end="\n", pretty=False, flush=False, from_critical=False) -> None`.
**Data Shape:** one append-only text file (`logs/log.txt`) receiving str() of every message; no buffering discipline beyond per-line open/append/close.

### Decisive source
```python
try:
    for message in msgs:
        pprint(message) if pretty else print(message, end=end, flush=flush)
        with open(__logs_file_path, 'a+', encoding="utf-8") as file:
            file.write(str(message) + end)
except Exception as e:
    trail = f'Skipped saving this message: "{message}"...' if from_critical else "We'll try one more time to log..."
    alert(f"log.txt in {logs_folder_path} is open or is occupied by another program! ... {trail}", "Failed Logging")
    if not from_critical:
        critical_error_log("Log.txt is open or is occupied by another program!", e)  # guarded retry
```

**Flow:** each call prints to console AND reopens/appends the mirror file → if the target is missing/unreadable, the user gets a MODAL alert (loud, unmissable on a desktop run) → unless this call already came FROM the critical path, it logs the logging failure itself once.
**Invariant:** the mirror never silently drops lines — failure is a visible modal; and the alert loop terminates because `from_critical=True` both changes the message and suppresses the nested `critical_error_log`. THE COST IS REAL: when nobody can dismiss the modal (headless, deleted logs/ dir), the process BLOCKS in tkinter mainloop — executed evidence this pass: removing `logs/` hung pytest at `pymsgbox._alertTkinter ← helpers.print_lg:137 ← modules.ai.connections.answer_question:294` (faulthandler stack under Xvfb); recreating the directory per the make_directories contract restored the full suite (57 ran / 56 passed / 1 live-skipped).
**Probe:** behavioral probes executed this pass: (RED) `rm -rf logs/ && python -m pytest tests/test_ai_connections.py` → collection-time hang, faulthandler names print_lg:137; (GREEN) `mkdir -p logs/` → same file 20 passed / 1 skipped; full suite green. Caveat: no unit test pins print_lg itself — its contract is pinned by this failure-mode experiment.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Auto_job_applier_linkedIn", query: "print_lg critical_error_log", limit: 6 });
// → modules.helpers.print_lg :126-139 · modules.helpers.critical_error_log :104-108
```

## Verdict
Adopt dual-write mirroring, loud-modal failure, and the from_critical recursion guard as a trio — they only make sense together. Adapt the alert surface for headless hosts (queue + stderr banner instead of a modal, or fail-soft skip WITH counter). Omit the blocking modal wherever no human sits at the machine; if you keep it, keep the startup make_directories contract that guarantees the target exists BEFORE the first log call.
