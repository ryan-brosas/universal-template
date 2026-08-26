<!-- capsule-v2 -->
# Lock vs lease — two ownership lifetimes over one shared browser profile

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** Which ownership primitive decides WHO may start a browser vs who is USING it, and how must each fail?

## Process-lifetime lock + reference-counted per-operation lease
**Path/Symbol:** `linkedin_mcp_server/daemon_lock.py` (434L, whole module); `linkedin_mcp_server/profile_lease.py:ProfileLease` (:354-546).
**Signature:** `DaemonLock.inheritable_copy()` (POSIX handover); `ProfileLease(auth_root)` with `.try_acquire()`, `.release()`, `.acquire(timeout)`, `.hold() -> _LeaseHandle`, `.announce() -> _Announcement`, `.held`, `.held_seconds`.
**Data Shape:** Lease files live under the resolved auth root (`<root>/.profile.lock`, `.handoff`); kernel flock on first acquire, released on last reference. `_reset_if_forked()` guards inherited state.

### Decisive source (the rules that cost measurements)
```text
daemon_lock.py:
- One holder, NO reference counting, released only on exit.
- Must not unlock before closing: a duplicate descriptor SHARES the lock,
  so unlocking through any copy releases it for all (measured both
  platforms). Release closes rather than unlocks.
  tests/test_daemon_lock.py:619 test_releasing_closes_rather_than_unlocks
- A free lock is NOT proof nothing runs: the kernel frees at instant of
  death while Chromium still shuts down (re-measured 13-38 ms / 11-103 ms;
  an earlier "over twenty seconds" claim was wrong and is recorded as such).
- Handover via inheritable fd works ONLY on POSIX: Windows child holding the
  inherited handle did NOT hold the lock after parent exit, 20 of 20 runs.
  tests/test_daemon_lock.py:463 test_windows_refuses_to_hand_a_lock_over

profile_lease.py ProfileLease:
- Reference counting is what makes per-process reuse safe: flock CONFLICTS
  WITH ITSELF across two open descriptions in one process, so middleware +
  browser creation locking again would self-deadlock.
  tests/test_profile_lease.py:85 test_reentrant_acquisition_does_not_self_deadlock
- auth_root resolved at construction so symlinked/relative spellings share
  one registry entry and one refcount.
- _reset_if_forked(): child CLOSES (never unlocks) the inherited fd — fork
  duplicates the descriptor and the lock lives as long as any copy is open;
  clearing bookkeeping alone would keep the parent's lease alive forever.
- mark_browser_closed() only after shutdown CONFIRMED — a timed-out cleanup
  may still be running; the flag stops auth state moving under it.
- Waiters announce intent (.announce/.handoff_requested) so an idle owner
  hands the browser over instead of holding it for process lifetime.
```

**Flow:** frontend election takes daemon lock (POSIX: before spawning owner, handing the child an inheritable copy; Windows: child competes) → every cooperating process takes lease refs around actual browser use → release on last ref → idle-owner handoff when waiters announced.
**Invariant:** Model ownership at TWO granularities — a considered-acquire/close-release process lock plus a refcounted per-use lease that errs toward hold-on-uncertain-teardown. Neither alone suffices; together with the browser's own SingletonLock they form the three-signal contract. All three must fail CLOSED: unverifiable owner refuses access.
**Probe:** `tests/test_daemon_lock.py` (714L), `tests/test_profile_lease.py` (992L), `tests/test_profile_lease_integration.py` (1,594L).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "ProfileLease DaemonLock inheritable_copy try_acquire", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-granularity ownership split and fork-reset discipline for any multi-process resource. Adapt file locations and handoff protocol. Omit Windows-specific Overlapped locking internals (platform detail).
