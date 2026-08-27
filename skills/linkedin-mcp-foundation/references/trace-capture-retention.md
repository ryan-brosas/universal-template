<!-- capsule-v2 -->
# Trace capture with on-error retention — ephemeral by default, kept only when something went wrong or was asked

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you capture diagnostic traces (screenshots, page state, logs) on EVERY run by default without leaking them to disk afterwards, and how do you make the keep/delete decision honest when several independent signals can each demand retention?

## debug_trace.py + logging_config.py — one retention state machine, two consumers
**Path/Symbol:** `linkedin_mcp_server/debug_trace.py` — `_trace_mode` (:24-31), `get_trace_dir` (:47-68), `mark_trace_for_retention` (:70-77), `should_keep_traces` (:79-81), `cleanup_trace_dir` (:83-96), `record_page_trace` (:117-190); `linkedin_mcp_server/logging_config.py` — `configure_logging` (:90-150), `teardown_trace_logging` (:152-165); teardown call site `cli_main.py:main.finally` (:634).
**Signature:** `get_trace_dir() -> Path | None`; `mark_trace_for_retention() -> Path | None`; `should_keep_traces() -> bool`; `teardown_trace_logging(*, keep_traces: bool = False) -> None`.
**Data Shape:** Module state: `_TRACE_DIR` (ephemeral mkdtemp under `auth_root/trace-runs`, or the explicit dir), `_TRACE_KEEP` (set by error paths), `_EXPLICIT_TRACE_DIR`. Env: `LINKEDIN_TRACE_MODE` ∈ off/on_error/always (default **on_error**), `LINKEDIN_DEBUG_TRACE_DIR` (explicit dir wins). Artifacts: `screens/NNN-slug.png` + appended `trace.jsonl` (pre-created O_EXCL 0o600) + `server.log` in the same dir.

### Decisive source
```python
# :24-31 — the default is on_error, not off: traces exist during every run
raw = os.getenv("LINKEDIN_TRACE_MODE", "").strip().lower()
if raw in {"off", "false", "0", "no"}:
    return "off"
if raw in {"always", "keep", "persist"}:
    return "always"
return "on_error"

# :79-81 — retention is a disjunction of three independent signals
def should_keep_traces() -> bool:
    return _EXPLICIT_TRACE_DIR or _TRACE_KEEP or _trace_mode() == "always"

# logging_config.py :138-143 — atexit delegates the keep/delete decision;
# registered exactly once
if not _TRACE_CLEANUP_REGISTERED:
    # The atexit fallback intentionally delegates the keep/delete
    # decision to teardown_trace_logging(), which re-checks runtime
    # trace retention state via cleanup_trace_dir().
    atexit.register(teardown_trace_logging)
    _TRACE_CLEANUP_REGISTERED = True

# cli_main.py :634 — the finally path passes the LIVE decision
finally:
    teardown_trace_logging(keep_traces=should_keep_traces())
```
**Flow:** get_trace_dir → explicit env dir wins (never deleted), else mode off ⇒ None, else ephemeral mkdtemp under the auth root → configure_logging attaches a file handler into that dir (server.log pre-created O_EXCL 0o600) → error paths call mark_trace_for_retention() → at exit, teardown_trace_logging(keep_traces=should_keep_traces()) closes the handler and rmtrees the dir unless an explicit dir, a retention mark, or mode=always says keep. record_page_trace is best-effort per field: every page access (title, body, locator, cookies, screenshot) is individually wrapped so one dead page cannot kill the capture; it records cookie NAMES only (never values), a whitespace-collapsed body_marker truncated to 200 chars, and appends one JSON line per step.
**Invariant:** The trace dir exists DURING the run even though it is usually deleted after — that is what lets logging attach a file handler by default; retention is decided at TEARDOWN time from live state, never frozen at startup. The cross-seam trap measured in-repo: configure_logging creates the trace dir INSIDE the auth root BEFORE the profile-root claim runs, which made a genuinely empty custom root read as occupied and refuse every first run — the real-startup test exists precisely because stubbing configure_logging hides the interaction. Cookie values must never reach a trace artifact; names are enough to tell which session was present.
**Probe:** `tests/test_debug_trace.py` (whole, 114L) — ephemeral-by-default, cleanup-removes, mark-retains, explicit-dir-preserved, mode-off-disables, step-counter-reset; `tests/test_logging_config.py` (whole, 62L) — atexit registered exactly once across repeated configure_logging calls, and the registered callback removes the ephemeral dir AND the FileHandler; `tests/test_cli_main.py::test_a_fresh_custom_root_really_claims_through_the_real_startup` (:683-725) — the un-stubbed real-startup case where logging's own footprint must not defeat the claim.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "get_trace_dir should_keep_traces mark_trace_for_retention teardown_trace_logging", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-signal retention disjunction (explicit dir OR runtime mark OR always-mode) with the decision re-checked at teardown, plus per-field best-effort capture and names-not-values for credentials, for any long-running process that should be diagnosable out of the box. Adopt the O_EXCL 0o600 pre-create for any artifact that may hold session material. Adapt the auth-root placement — and if your own startup has a destructive-root guard, order it against this side effect deliberately (the source's measured first-run refusal is the failure mode of getting that ordering wrong). Omit the LinkedIn-specific page fields. Coverage caveat: none — both modules fully indexed at the pin (no_recorded_issue); graph unavailable this pass, citations verified by direct read.
