<!-- capsule-v2 -->
# Lease-object settle — why must teardown settle the exact object it acquired?

**Source:** linkedin-mcp-server Apache-2.0 `main@0cd1e5fb`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you hand back a shared resource when the close may fail halfway and cancellation is deliberately deferred?

## Keep the object, never re-derive it
**Path/Symbol:** `linkedin_mcp_server/drivers/browser.py:_settle_the_profile` (:796), `_close_browser_locked` (:848), `_run_deferring_cancels` (:776); global `_browser_lease` held since create (:89 comment block documents six review rounds).
**Signature:** `def _settle_the_profile(*, confirmed: bool) -> None` — never raises; runs mid-teardown possibly with an exception already propagating.
**Data Shape:** `_browser_lease: ProfileLease | None` is always the object `get_profile_lease()` handed out (never locally constructed: fork-reset walks that registry, and an outside instance would silently keep a parent's kernel lock alive in a child).

### Decisive source
```text
lease, _browser_lease = _browser_lease, None   # swap-and-forget FIRST
if lease is None:
    return                                     # middleware already held it
if confirmed:                                  # Chromium PROVABLY gone
    lease.mark_browser_closed()
    lease.release()                            # only NOW may auth state move
    return
_browser_lease = lease                         # keep BOTH: Chromium may live
logger.warning("...keeping the profile lease until this process exits.")
a_held_profile_means_this_owner_must_go(lease)  # asked WHERE THE LEASE IS KEPT,
# not where failure is reported: this path returns NORMALLY from handoffs, the
# idle timeout and close_session — no exception exists to hang a request on.

The refactor this encodes: recording only THAT a lease existed left the close
to reconstruct it via get_profile_lease(), which resolves a path and can FAIL
while _browser is already cleared and every safety line sits below the call —
ownership inferred from two globals that could disagree, settled at the moment
one of them was gone.

Cancellation deferral around teardown (_close_browser_locked callers):
    task = asyncio.create_task(coroutine)
    while True:
        try: result = await asyncio.shield(task); break
        except asyncio.CancelledError: cancelled = True
    if cancelled: raise asyncio.CancelledError
Shielding alone re-raises to the caller immediately and releases the lifecycle
lock while teardown still runs — exactly when a new launch must not start.

finally-placement: confirmed=False default; try: confirmed = await browser.close()
finally: _settle_the_profile(confirmed=confirmed) — anything raised between
clearing _browser and settling used to leave the profile held by a process
nobody had asked to give way.
```

**Flow:** close clears globals first → export cookies best-effort (debug-logged skip) → bounded close returns `confirmed` → settle swaps the lease out and either releases both markers or keeps everything and requests a successor owner.
**Invariant:** The settle decision consumes exactly one bit — is Chromium provably gone? — and every other outcome errs toward holding: an unconfirmed close wedges later launches into `BrowserBusyError` rather than risk double-launch corruption, and the kernel frees the lock at process exit as the backstop.
**Probe:** `grep -c '_settle_the_profile' linkedin_mcp_server/drivers/browser.py` → 2; `grep -c 'a_held_profile_means_this_owner_must_go' linkedin_mcp_server/drivers/browser.py` → 3; direct tests: `tests/test_daemon_election.py` real-owner attach refusals cited in-source (:609-611), `tests/test_browser_driver.py::test_same_runtime_start_failure_closes_browser` (:577).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "get_or_create_browser singleton create lock", limit: 5 });
```

## Verdict
Adopt keep-the-acquired-object settle semantics + cancel-deferring shield loop for any teardown that must complete despite caller cancellation. Adapt warning/stand-down signaling to your supervisor model. Omit flock specifics (see lock-vs-lease capsule).
