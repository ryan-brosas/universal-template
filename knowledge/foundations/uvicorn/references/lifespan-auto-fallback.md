<!-- capsule-v2 -->
# Lifespan auto-fallback and state dict — how does a lifespan-less app still boot, and how is startup state shared?

**Source:** Uvicorn BSD-3-Clause `main@9ee5694516b01f1d3d6ff9ed38f117fc869ee6ae`; Codebase Memory `ext-uvicorn`. **Question:** What distinguishes "protocol unsupported" from "startup failed", and what does the GC comment protect?

## auto+BaseException ⇒ info-log and continue; explicit on ⇒ error; task ref held
**Path/Symbol:** `uvicorn/lifespan/on.py` — task-ref noqa :51, startup decision :56–64, shutdown mirror :70–78, `main` classification :80–97, transition asserts :107–131.
**Signature:** `async def startup(self) -> None` / `async def main(self) -> None`; events `startup_event/shutdown_event: asyncio.Event`, queue `receive_queue`.
**Data Shape:** `self.state: dict[str, Any]` — SAME dict object handed to every request scope via `"state": self.app_state.copy()` (shallow per-request copy of the shared dict).

### Decisive source
```python
# :50-53 — keep a hard reference; a fire-and-forget task can be GC'd mid-await
main_lifespan_task = loop.create_task(self.main())  # noqa: F841
# Keep a hard reference to prevent garbage collection  (Kludex/uvicorn#972)
...
# :88-96 — the fallback classifier
except BaseException as exc:
    self.asgi = None
    self.error_occurred = True
    if self.startup_failed or self.shutdown_failed:
        return                                   # app signalled failure itself
    if self.config.lifespan == "auto":
        msg = "ASGI 'lifespan' protocol appears unsupported."
        self.logger.info(msg)                    # WSGI/ASGI2 apps land here
    else:
        self.logger.error("Exception in 'lifespan' protocol\n", exc_info=exc)
finally:
    self.startup_event.set(); self.shutdown_event.set()
```

**Flow:** startup(): spawn `main()` task, push `lifespan.startup` into receive_queue, await the event. App replies complete/failed through send() whose asserts ENFORCE ordering (no shutdown-complete before startup-complete). If the app callable itself crashes (e.g. plain WSGI object that ignores the lifespan scope), `error_occurred` + `lifespan=="auto"` downgrades to an INFO log and serving continues; with `lifespan=="on"` the same crash is fatal (`should_exit=True`). Server.shutdown skips the shutdown phase entirely when `error_occurred` (:71–72).
**Invariant:** The `state` dict must be populated during startup and read-copied per request — mutations after startup are NOT propagated to already-created scopes. Both completion events are ALWAYS set in `finally`, so a crashed lifespan can never hang the server's startup()/shutdown() awaits.
**Probe:** from the uvicorn checkout root: `bash -c "grep -c 'noqa: F841' uvicorn/uvicorn/lifespan/on.py"` → 1; `bash -c "grep -c 'protocol appears unsupported' uvicorn/uvicorn/lifespan/on.py"` → 1; `bash -c "grep -cF 'self.config.lifespan == \"on\"' uvicorn/uvicorn/lifespan/on.py"` → 2. Behavioral pins: `tests/test_lifespan.py:test_lifespan_with_failed_startup` :131 and the auto-vs-on parametrization family.
**Retrieve:** `search_graph {"project":"ext-uvicorn","query":"lifespan protocol appears unsupported startup failed","limit":5,"detail":"ids"}` → rank#1 `test_lifespan_with_failed_startup` :131-157 line-exact.
**Verdict:** Adopt the auto-fallback classifier and always-set-finally pattern verbatim. Adapt logging levels. Omit LifespanOff (trivial no-op stub).

