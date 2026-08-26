<!-- capsule-v2 -->
# Session rotation — how do you retire a live profile without risking the user's login?

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** What is the safe discipline for moving aside an authenticated browser profile before a new login?

## Move-don't-delete + atomic restore + peer guards
**Path/Symbol:** `linkedin_mcp_server/session_state.py:rotate_source_profile()` (:797), `rotate_shielded()` (:605), `restore_source_profile()` (:896), `a_peer_already_signed_in()` (:767).
**Signature:** `rotate_source_profile(source_profile_dir=None, *, superseded_by: str | None | object = UNGUARDED)`; quarantine dir `<auth_root>/invalid-state-<ts>-<uuid8>/`.
**Data Shape:** `superseded_by` tri-state: `UNGUARDED` sentinel = no guard requested; `None` = nothing-to-retire expected; a generation uuid = raise if a DIFFERENT usable session appeared. Outcomes: retired path, or `None` (nothing there), or `PeerSessionInPlaceError`.

### Decisive source
```python
class PeerSessionInPlaceError(RuntimeError):
    """A peer replaced the session this rotation was asked to retire.

    Raised rather than returned as ``None``, which already means "there was
    nothing to retire". The two look identical to a caller and are not: one is
    a no-op, the other means somebody else has done the work and this caller
    should stop rather than carry on as though it had. Measured with them
    conflated: the caller went on to promise a login window that never opened.
    """
```
Why rotate at all: Chromium mints `machine_id` into `Local State` once per profile — reusing the directory for another account hands LinkedIn the same device identity twice, linking accounts.

**Flow:** hold lease → guard check (`state.login_generation != superseded_by` AND `_auth_ready()` both required) → move profile+sidecars to timestamped+uuid-suffixed quarantine → new login writes fresh generation. Partial move failure RESTORES what moved before raising; restore re-retires on partial failure rather than straddling.
**Invariant:** (1) Never delete auth state — quarantine it; a session that turns out fine stays recoverable (`--logout` clears quarantines). (2) Callers see old-intact or fully-retired, never split. (3) None / Error / sentinel mean different things callers act on — conflating them promised logins that never opened. (4) Restore refuses unless source-state + non-empty profile + cookies.json ALL exist (debris ≠ replacement); `_our_quarantine` validates name AND location so foreign content can't be injected into an owned root.
**Probe:** `tests/test_session_state.py:516` `test_lock_from_another_host_counts_as_held`, `:502 test_restore_ignores_a_half_written_marker`, `:452 test_restores_over_an_abandoned_profile_dir`.

## Cancel-deferral around the move
**Path/Symbol:** `session_state.py:run_deferring_cancels()` (:580), `rotate_shielded()` (:605).
**Signature:** `run_deferring_cancels(work) -> tuple[Any, bool]` via `loop.run_in_executor` + `asyncio.shield` loop.
**Data Shape:** Returns (result, cancel_arrived); caller restores then re-raises.

### Decisive source
```python
# Uses ``run_in_executor`` rather than ``to_thread``: the latter registers an
# ``asyncio.Task``, which ``asyncio.run`` cancels along with everything else
# at loop teardown. Shielding an already-cancelled *task* re-raises forever,
# so the wait below would spin and the process would never exit. A bare
# Future is not in ``all_tasks()`` and never reaches that state.
```
**Flow:** shield-spin collecting cancels → if cancelled and rotation succeeded → restore backup → raise `CancelledError` once at the end.
**Invariant:** A cancel landing after the thread moved the session strands the user logged out — defer cancels until the session is accounted for or restored. NEVER `asyncio.to_thread` here (its Task lands in `all_tasks()` and blocks loop teardown).
**Probe:** `tests/test_session_state.py` cancellation tests pin defer-then-reraise behavior.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "rotate_source_profile quarantine restore PeerSessionInPlaceError", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt move-not-delete, atomicity-with-restore, tri-state peer guard, cancel-deferral ladder. Adapt quarantine naming. Omit Chromium machine_id rationale (LinkedIn-specific threat model).
