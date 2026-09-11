<!-- capsule-v2 -->
# Auth quiescence latch — how does an owner that cannot sign in stop re-opening a dead session?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** What stops the next tool call from launching Chromium on a session just proven broken while someone else logs in?

## Latch = broken generation + file-existence, lifted only by BOTH
**Path/Symbol:** `linkedin_mcp_server/bootstrap.py:go_auth_quiescent` (:1990), `_auth_quiescence_lifted` (:2017), `_raise_if_auth_quiescent` (:2033); gate entry `ensure_tool_ready_or_raise` (:1531) calls the raise check BEFORE any browser-reaching branch.
**Signature:** `def go_auth_quiescent(observed_generation: str | None) -> None`; `def _auth_quiescence_lifted() -> bool` = `_auth_ready() and current_login_generation() != _auth_quiescent_generation`.
**Data Shape:** Latch state is two module globals (`_auth_quiescent: bool`, `_auth_quiescent_generation: str | None`). `current_login_generation()` returns None for a rotated/absent profile — None is a VALUE, so "no session" vs "a session I have not seen" needs the second latch field.

### Decisive source
```text
def _raise_if_auth_quiescent() -> None:
    if not _auth_quiescent:
        return
    if _auth_quiescence_lifted():
        ...clear latch; return
    raise AuthStaleOnOwnerError(
        "...it cannot sign in by itself. Retry this tool: the client will
         open a login window.",
        nothing_ran_yet=True,          # gate runs AHEAD of the tool body
        generation=_auth_quiescent_generation,
        # The LATCHED generation, not a fresh reading: every call after the
        # first arrives here rather than through handle_auth_error, so omitting
        # it means the SECOND client repairs unguarded while the first signs in.

Why both halves (measured):
- changed-generation alone lifts on an ABANDONED login: the frontend rotates
  the profile first ⇒ generation reads None ≠ observed ⇒ owner opens Chromium
  on a profile with NO session at all.
- _auth_ready() alone never lifts: it tests file existence and was ALREADY
  true of the broken session.
A generation is only written after a login validated and exported its cookies.

Gate placement: ensure_tool_ready_or_raise runs _raise_if_auth_quiescent()
before Docker/custom-Chrome/setup branches — readiness is decided by whether
files EXIST, so every later path would reopen the dead session.
```

**Flow:** auth error handler confirms close, records the generation it found, latches → subsequent tool gates report AuthStaleOnOwnerError (client opens login window) → frontend rotates profile, signs in, writes new generation → next gate sees ready-files AND changed generation → latch clears, owner resumes.
**Invariant:** The latch must be checked before anything that can reach a browser, and its error must carry the latched generation so concurrent repairers serialize on one observation instead of each rotating on their own.
**Probe:** `grep -c '_auth_quiescent_generation' linkedin_mcp_server/bootstrap.py` → 9; `grep -c 'nothing_ran_yet=True' linkedin_mcp_server/bootstrap.py` → 2; direct tests: `tests/test_bootstrap.py::TestTheOwnerStaysQuiescentUntilANewSessionLands::test_the_broken_session_alone_never_lifts_it` (:4386), wired into handler via `tests/test_dependencies.py:276`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_start_login_if_needed go_auth_quiescent superseded", limit: 5 });
```

## Verdict
Adopt two-field quiescence latches for any shared resource whose readiness checks are existence-based. Adapt generation tokens to your mutation counter scheme. Omit MCP progress-report plumbing.
