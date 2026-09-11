<!-- capsule-v2 -->
# gdb-dap-deferred-cancellation — how does a DAP server answer slow requests without breaking cancellation?

**Source:** JetBrains CLion installed build `2026.2.1@262.9437.136` (`bin/gdb/linux/x64/share/gdb/python/gdb/dap/server.py`, upstream GDB's bundled DAP server shipped inside the IDE); Codebase Memory `jetbrains-clion`. **Question:** How do you serve a JSON-RPC debug protocol where some requests take seconds, must remain cancellable mid-flight, and may finish AFTER newer commands arrive?

## DeferredRequest + CancellationHandler
**Path/Symbol:** `gdb/dap/server.py`: `Server.invoke_request` (:266-301), `DeferredRequest.set_request/invoke/reschedule` (:55-105), `CancellationHandler` (:127-180, fields in `__init__`), `NotStoppedException`.
**Signature:** `invoke_request(req, result, fn)`; a request fn returns either a result body or a `DeferredRequest`; `reschedule()` later calls `invoke()` under `canceller.current_request(req)` and sends the response.
**Data Shape:** cancellation state = one `threading.RLock` guarding `in_flight_dap_thread`, `in_flight_gdb_thread`, a queue of pending cancels and `_deferred_ids: set` of unresolved deferred requests. Error mapping is part of the wire contract: `NotStoppedException -> "notStopped"`, `KeyboardInterrupt -> "cancelled"`, `DAPException -> str(e)`, `BaseException -> logged + str(e)`.

### Decisive source
```python
# Server.invoke_request (retrieved via mcp get_code_snippet, :266-301)
try:
    self.canceller.check_cancel(req)
    fn_result = fn()
    result["success"] = True
    if isinstance(fn_result, DeferredRequest):
        fn_result.set_request(req, result)
        self.canceller.defer_request(req)
        # Do not send a response.
        return
    elif fn_result is not None:
        result["body"] = fn_result
except NotStoppedException:
    result["success"] = False
    result["message"] = "notStopped"
except KeyboardInterrupt:
    # This can only happen when a request has been canceled.
    result["success"] = False
    result["message"] = "cancelled"
...
self.canceller.request_finished(req)
self._send_json(result)
```

**Flow:** request lands on the DAP thread → `check_cancel` raises `KeyboardInterrupt` if cancelled → `fn()` runs → ordinary body ⇒ respond immediately; `DeferredRequest` ⇒ register id, send NOTHING → later `reschedule()` re-enters the canceller context (optionally deferring events via `defer_events()`), invokes, emits pending events. Every exit path calls `request_finished` (discard, not remove — deferred ids may never have been added).
**Invariant:** a deferred request holds NO response slot — the client sees silence until reschedule; cancellation must stay correct for requests that are (a) queued, (b) in-flight on either thread, or (c) deferred-but-unresolved; cancel is signalled by exception (`KeyboardInterrupt`), not return codes.
**Probe:** executed byte-exact pre-write: `grep -nF '"notStopped"' .../server.py` → `:282`; `grep -nF '"cancelled"' ...` → `:286`; AST class census → `['Cancellable','CancellationHandler','DeferredRequest','Invoker','NotStoppedException','Server']`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "jetbrains-clion", qualified_name: "jetbrains-clion.bin.gdb.linux.x64.share.gdb.python.gdb.dap.server.Server.invoke_request" });
await mcp.codebase_memory.search_graph({ project: "jetbrains-clion", query: "dap server request dispatch launch", limit: 8 });
```
(both executed live this pass; coverage no_recorded_issue / metadata_match.)

## Verdict
Adopt the deferred-request pattern (return-a-sentinel instead of blocking the reader thread) and the exception-keyed error ladder for any DAP/LSP-style server; adapt the two-thread in-flight tracking to your threading model; omit GDB-specific inferior control. Coverage caveat: upstream GDB code, verified as shipped data plane.
