<!-- capsule-v2 -->
# Login claim ladder — how do concurrent pollers share one login (or import) without colliding on the profile?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How do multiple clients trigger one repair — and never a headed login on top of an in-flight import?

## Claim under lock, await outside it, generation-guards throughout
**Path/Symbol:** `linkedin_mcp_server/bootstrap.py:_start_login_if_needed` (:1811), `invalidate_auth_and_trigger_relogin` (:2058), `_try_auto_import_session` (:1723), `_auto_import_allowed` (:1625), `wait_for_login_to_finish` (:1952).
**Signature:** `async def _start_login_if_needed(ctx=None, *, superseded_by: str | None | object = UNGUARDED) -> None` — UNGUARDED sentinel ≠ None: "observed nothing" is distinct from "observed no session" (conflating them measured as: reports a window opened, opens none, keeps dead session, readiness says fine).
**Data Shape:** `BootstrapState` carries `login_task`, `import_task`, `import_attempted` (one-shot per episode), `login_supersedes`, `last_error`; tasks are shared so every poller awaits the SAME task.

### Decisive source
```text
Branch order under _lock (cheap claims only; slow work AFTER release):
1. OWNER role → raise AuthMissingOnOwnerError(nothing_ran_yet=True) ahead of
   EVERY branch — auto-import rotates profiles, headed login needs a desktop.
2. _auth_ready() → done.
3. login_task in flight → await THE SAME task. Never spawn anything on top.
4. else import_task in flight → await IT; spawning a headed login would open a
   SECOND persistent context on the same user_data_dir and collide on
   Chromium's SingletonLock.
5. else not import_attempted and _auto_import_allowed() → claim one-shot:
   import_attempted=True; login_supersedes=superseded_by; create task named
   "linkedin-auto-import".
6. else manual-login path: _move_invalid_auth_state_aside(superseded_by) →
   state STARTING → create "linkedin-login" task.

Inline wait (#535): asyncio.wait({task}, timeout=budget) — NEVER wait_for,
which CANCELS on timeout and would kill a browser somebody is typing into;
timeout leaves the task RUNNING, then re-reads filesystem truth (_auth_ready).

Import failure re-enters (import_attempted now True ⇒ takes branch 6, no loop).
ProxyConnectionError re-raised at BOTH layers (it subclasses NetworkError):
a dead proxy is not a missing session; swallowing would send the user into a
manual login that fails through the same proxy.

Auto-import guard rails (_auto_import_allowed, flag check MUST stay first):
explicit-False disables; DOCKER no host keychain; OWNER role (frontend imports
instead — it has the desktop session AND holds the profile); proxy configured
(imported session was created on the real IP → silent proxy move trips
checkpoints); streamable-http bound NON-loopback (network daemon must never
harvest host cookies on remote requests). Bind-address gate covers network-
exposed HTTP only, NOT stdio-over-SSH (keychain decrypt simply fails there).

invalidate_auth_and_trigger_relogin: force-move failures are LOGGED not fatal —
the login WAITS for the profile now (rotate_shielded), so refusing throws away
the wait; then resets import_attempted=False (fresh episode) and starts the
login with stale_generation traveling as login_supersedes.

wait_for_login_to_finish(timeout) — the ONE place that waits instead of
raising-by-reporting-started; reads the task (not readiness polling) because a
FAILED login must end the wait too; returns filesystem truth; timeout leaves
the login running (cancelling strands a half-finished sign-in).
```

**Flow:** tool gate finds auth missing → owner-role report OR one-shot bounded auto-import (60s hard ceiling via `asyncio.wait_for`) OR shared headed login with inline budget → poll-friendly AuthenticationInProgressError tells the client to retry in ~30s → success is always re-decided from disk truth.
**Invariant:** At most one profile-touching browser per user_data_dir per process episode, achieved by sharing tasks (never duplicating work) and by the UNGUARDED-generation guards that make a loser stand down when a peer's session landed while it waited (`a_peer_already_signed_in`).
**Probe:** `grep -c 'asyncio.wait({login_task}, timeout=budget)' linkedin_mcp_server/bootstrap.py` → 1; `grep -c 'import_attempted = False' linkedin_mcp_server/bootstrap.py` → 1; direct tests: `tests/test_bootstrap.py::TestTheOwnerStaysQuiescentUntilANewSessionLands` (:4375ff); peer-guard integration `tests/test_profile_lease_integration.py:1376`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "_start_login_if_needed go_auth_quiescent superseded", limit: 5 });
```

## Verdict
Adopt task-sharing claim ladders + sentinel generation guards for any concurrent self-repair of shared state. Adapt import sources/keystore bounds to your platform. Omit macOS keychain specifics (see browser_import capsule for that pipeline).
