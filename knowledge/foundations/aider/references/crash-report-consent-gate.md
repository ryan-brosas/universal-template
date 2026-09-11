<!-- capsule-v2 -->
# Uncaught-exception report gate — consent-first crash reporting with scrubbed system info

**Source:** Aider Apache-2.0 `main@5dc9490bb35f9729ef2c95d00a19ccd30c26339c`; Codebase Memory project `aider`. **Question:** Should a CLI agent auto-upload crash reports, and if the user consents, what may leave the machine?

## sys.excepthook installed at main() entry; report only after an explicit per-crash confirm; no-ops without consent
**Path/Symbol:** `aider/report.py`: `report_uncaught_exceptions()` (:15, installs `sys.excepthook = except_hook`), `except_hook(...)` (:23), `report_github_issue(exception, args=None, error_log=None)` (:44), `confirm_ask` gating inside (:78-84), `sys_info(args)` (:100-160, collects OS/python/litellm versions + git status of cwd).
**Signature:** `report_github_issue` returns early unless `io.confirm_ask("View the suggested prompt to file a GitHub issue?")` — nothing is sent automatically; the "report" is a PRE-FILLED issue TITLE/BODY handed to webbrowser.open on a github.com login redirect.
**Data Shape:** issue body embeds the exception traceback + `sys_info()` block (platform, python, aider version, litellm version); NO chat content, file contents, or API keys are collected.

### Decisive source
```python
def report_uncaught_exceptions():
    sys.excepthook = except_hook
...
def except_hook(type, value, tb):
    sys.__excepthook__(type, value, tb)
    if is_first_run_of_new_version(...) or confirm_ask(...):
        report_github_issue(value)
```
(first line ALWAYS chains the default hook so stderr still shows the traceback)

**Flow:** main() :452 calls report_uncaught_exceptions() before anything else → any uncaught exception prints normally AND offers the issue flow → user consents → title derived from exception type/message → body assembled with traceback + versions → browser opens github.com/login?...next=issue-template URL.
**Invariant:** telemetry-by-navigation: the only network egress is the USER's own browser hitting github.com — the agent itself performs no upload; chaining __excepthook__ first guarantees crash visibility even when reporting declines.
**Probe:** NO dedicated upstream test file exists for report.py (`grep -rln report_github_issue tests/` finds nothing direct; source-pinned caveat). Deterministic anchors: `grep -nF 'sys.excepthook' aider/report.py` → exactly :19; `grep -nF 'report_uncaught_exceptions' aider/main.py` → :36 import + :452 call.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aider", query: "report_uncaught_exceptions", limit: 3 });
// resolves report.py hooks + main.py install site
```

## Verdict
Adopt the consent-first crash-report pattern verbatim for developer tools; adapt the issue-template URL. Porters who skip the excepthook chain lose stack traces; porters who skip confirm_ask ship covert telemetry — both halves are load-bearing.
