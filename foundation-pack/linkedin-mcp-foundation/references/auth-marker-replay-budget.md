<!-- capsule-v2 -->
# Auth marker across the hop — error results that survive masking, and budgeted repair replays

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb2907`; Codebase Memory `linkedin-mcp-server`. **Question:** How does a browser-owning process ask a headless frontend process to sign in on its behalf — and when may the frontend re-run the failed call?

## OwnerAuthSignalMiddleware + FrontendAuthRepairMiddleware
**Path/Symbol:** `linkedin_mcp_server/daemon_auth.py` — signal middleware (:152-204), marker schema constants (:113-134), `_readable_marker` (:384-409), repair middleware (:224-350), `a_repeat_could_change_something` (:353-381), budget helpers (:69-110).
**Signature:** `ToolResult(content=[TextContent(str(exc))], meta={MARKER_KEY: marker}, is_error=True)`; marker = `{v: 2, reason: "missing"|"stale", replayable: bool, browser_open: bool, generation: str|None}`.
**Data Shape:** Two fields answer different questions: `reason` says what to repair; `replayable` says whether work had happened when it failed. Neither implies the other.

### Decisive source
```python
# :200-204 — an error RESULT, because mask_error_details strips raised types
# (measured fastmcp 3.4.4: re-raise delivered meta=None + generic text)
return ToolResult(
    content=[mt.TextContent(type="text", text=str(exc))],
    meta={MARKER_KEY: marker},
    is_error=True,   # a raising client still gets its ToolError
)

# :275-294 — a STARTED login is one step before success, not a failure
except (AuthenticationStartedError, AuthenticationInProgressError):
    left = _how_long_to_wait_for_the_sign_in(
        self._tool_timeout, time.monotonic() - began)
    if not await _wait_for_the_sign_in(left):
        return result

# :309-331 — even after successful repair, never auto-repeat mutations
if await a_repeat_could_change_something(context):
    return result        # measured orphan effects: ['sent'] then ['sent','sent']
```
**Flow:** owner middleware catches `OwnerCannotAuthenticateError` in the cause chain → emits marker result (is_error kept true) → frontend reads it, refuses while `browser_open` (lease still held; unconfirmed teardown keeps it set), repairs locally (`start_login_if_needed(superseded_by=generation)` / `invalidate_auth_and_trigger_relogin(stale_generation=…)`), waits out started logins inside a fraction of the remaining call budget, then replays only read-only calls bounded by what is left of the budget.
**Invariant:** Marker version tolerance is FORWARD-only (older frontend × newer owner is the supported skew; reverse cannot arise — a newer frontends stands old owners down). `generation` travels from the FAILURE, never re-read from disk, so two frontends cannot rotate each other's fresh sessions. Unknown/undeclared tools count as MUTATING (`readOnlyHint` or nothing). One shared replay predicate serves both middlewares so they cannot drift in the unsafe direction.
**Probe:** `tests/test_daemon_auth.py` — `TestTheMarkerSurvivesTheHop` (:88-160): marker reaches outer client through a real proxy with reason/replayable intact, owner wording preserved, unrelated failures unmarked; role tests :762-810 pin only-owner-signals / only-proxy-repairs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "OwnerAuthSignalMiddleware FrontendAuthRepairMiddleware MARKER_KEY marker", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt result-carried structured markers (not exceptions) whenever an error must cross a forwarding layer that masks details; adopt generation-stamped repair plus annotation-gated, budget-bounded replays for any multi-process auth-repair design. Adapt the budget fraction/floor to your timeout model. Omit LinkedIn-specific reasons. Coverage caveat: none — module fully indexed.
