<!-- capsule-v2 -->
# Daemon entry lifecycle — what must happen between process start and clean exit?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** What is the singleton guard, log/pid setup, and shutdown choreography of the daemon process itself?

## Ping-guarded idempotent startup + guaranteed teardown
**Path/Symbol:** `src/browser_harness/daemon.py:already_running/serve/__main__` (:668-729).
**Signature:** module-level NAME/LOG/PID resolved from BU_NAME at import; `serve(d)` races serve_task vs stop_event task with FIRST_COMPLETED; 0.05s sleep after bind so the "listening on" log line resolves the live endpoint.
**Data Shape:** pid file written AFTER ping guard passes; log TRUNCATED (`"w"`) per fresh boot so admin's last-line triage reads only THIS boot.

### Decisive source
```python
if __name__ == "__main__":
    if already_running():
        print(f"daemon already running on {SOCK}", file=sys.stderr)
        sys.exit(0)
    open(LOG, "w").close()
    open(PID, "w").write(str(os.getpid()))
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        log(f"fatal: {e}")
        sys.exit(1)
    finally:
        stop_remote()
        try: os.unlink(PID)
        except FileNotFoundError: pass
```

**Flow:** ping guard exits 0 (not error) when alive — spawn loops rely on double-start being harmless → truncate log → write pid → serve until stop or crash → finally: cancel tasks, cleanup endpoint, PATCH-stop cloud browser (billing!) even on unexpected death, remove pid file.
**Invariant:** Double-spawn must be SAFE (exit 0) because ensure_daemon races spawns; log truncation is what makes ensure_daemon's read-last-line classification valid; `finally: stop_remote()` guarantees billed-resource teardown even when the event loop dies — the process-local twin of start_remote_daemon's compensation.
**Probe:** `tests/unit/test_daemon.py:537-561` pins real serve-shutdown leaving working/user tabs intact; singleton guard shares the ping contract pinned in `tests/unit/test_ipc.py`. Full __main__ flow untested directly (process-level) — coverage caveat.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "serve stop event shutdown pid", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt ping-guarded idempotent startup + per-boot log truncation + guaranteed remote-resource teardown in finally. Adapt signal handling to your host. Omit cloud stop when no metered resource exists.
