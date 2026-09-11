<!-- capsule-v2 -->
# Process-exit sandbox cleanup — how do orphaned temp working dirs get reclaimed when async destroy() never ran?

**Source:** pipeshub-ai Apache-2.0 `main@4a02110dd9a7a644d8ba7a5ccd295c58a3c3628f`; Codebase Memory `pipeshub-ai`. **Question:** How does a library (not the process owner) install atexit + signal cleanup that reclaims sandbox dirs WITHOUT clobbering the host app's own signal handling?

## Register/unregister set + handler-chaining signal ladder
**Path/Symbol:** `backend/python/app/agent_loop_lib/sandbox/coding/cleanup.py:register_sandbox_dir/unregister_sandbox_dir/_signal_handler/_ensure_installed` (L33–87).
**Signature:** `register_sandbox_dir(path) -> None` (called by every backend's `provision()`); `unregister_sandbox_dir(path) -> None` (after a normal `destroy()`); `_cleanup_all() -> None` — deliberately SYNCHRONOUS (`atexit` cannot await).
**Data Shape:** Module-global `_registered_dirs: set[str]` under a `threading.Lock`; one-shot `_installed` latch; saved `_prev_sigterm/_prev_sigint`.

### Decisive source
```python
def _signal_handler(signum, frame):
    _cleanup_all()
    prev = _prev_sigterm if signum == signal.SIGTERM else _prev_sigint
    if callable(prev):
        prev(signum, frame)              # CHAIN, don't clobber
    elif prev == signal.SIG_DFL:
        signal.signal(signum, signal.SIG_DFL)
        signal.raise_signal(signum)      # restore default semantics

def _ensure_installed():
    ...
    try:
        _prev_sigterm = signal.getsignal(signal.SIGTERM)
        _prev_sigint  = signal.getsignal(signal.SIGINT)
        signal.signal(signal.SIGTERM, _signal_handler)
        signal.signal(signal.SIGINT,  _signal_handler)
    except (ValueError, OSError):
        pass   # not main thread / unsupported platform → atexit still covers
```

**Flow:** backend `provision()` registers its dir → hooks installed once, lazily → normal path: `destroy()` removes dir + unregisters so the sweep is a no-op → crash/kill path: SIGTERM/SIGINT handler or atexit sweeps all still-registered dirs with `shutil.rmtree(ignore_errors=True)` then chains to whatever handler was there before.
**Invariant:** (1) A LIBRARY must chain pre-existing signal handlers, never replace them — the host application owns the process's signal policy. (2) Cleanup is best-effort rmtree only; it can never call the real async `destroy()` (backend-specific teardown) — local disk hygiene, nothing more. (3) Unregister-on-normal-destroy prevents redundant sweeps of already-gone dirs. (4) All shared state mutated under one lock; handler installation tolerated to fail off-main-thread.
**Probe:** No direct unit suite for `cleanup.py` at HEAD (`register_sandbox_dir` appears in no tests/ file) — coverage caveat recorded; deterministic probes: source-symbol grep + retrieval of `register_sandbox_dir`. Signal-chaining behavior verified by read only.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pipeshub-ai", query: "register_sandbox_dir unregister_sandbox_dir _cleanup_all _signal_handler", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the register/sweep/unregister lifecycle + handler-chaining pattern for ANY library that creates temp artifacts it can't always tear down politely; adapt signal set (add SIGHUP on POSIX daemons). Coverage caveat stands — port from source with care since no test pins the chaining order.
