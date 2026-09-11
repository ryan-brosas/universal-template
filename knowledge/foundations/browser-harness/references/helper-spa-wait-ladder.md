<!-- capsule-v2 -->
# SPA wait ladder — why does readyState lie, and which wait matches which async-render failure?

**Source:** browser-harness MIT `main@41108b8676d4bdb58b26ab3b079c0b7b0f8f3926`; Codebase Memory `browser-harness`. **Question:** A page is 'complete' but the framework hasn't rendered; how do three waits each fix a distinct SPA failure mode?

## readyState / checkVisibility / Network-idle, each tuned to one failure
**Path/Symbol:** `src/browser_harness/helpers.py:wait_for_load` (:387-393), `wait_for_element` (:395-423), `wait_for_network_idle` (:425-458).
**Signature:** `wait_for_load(timeout=15.0) -> bool`; `wait_for_element(selector, timeout=10.0, visible=False) -> bool`; `wait_for_network_idle(timeout=10.0, idle_ms=500) -> bool`.

### Decisive source
```python
# wait_for_element(visible=True): checkVisibility walks ANCESTORS — a
# getComputedStyle check on the element alone returns the descendant's own
# style, NOT the inherited "is this rendered" state.
check = (f"(()=>{{const e=document.querySelector({json.dumps(selector)});if(!e)return false;"
         f"if(typeof e.checkVisibility==='function')"
         f"return e.checkVisibility({{checkOpacity:true,checkVisibilityCSS:true}});"
         f"const s=getComputedStyle(e);"
         f"return s.display!=='none'&&s.visibility!=='hidden'&&s.opacity!=='0'}})()")

# wait_for_network_idle: filter events to the ACTIVE session — a background
# polling/SSE tab keeps emitting Network.* and would poison the idle window.
active_session = _send({"meta": "session"}).get("session_id")
for e in drain_events():
    if e.get("session_id") != active_session: continue
    if e.get("method") == "Network.requestWillBeSent":
        inflight.add(e["params"].get("requestId")); last_activity = time.time()
    elif e.get("method") in ("Network.loadingFinished", "Network.loadingFailed"):
        inflight.discard(e["params"].get("requestId")); last_activity = time.time()
```

**Flow:** `wait_for_load` polls `document.readyState == 'complete'` (misses SPAs); `wait_for_element` polls `querySelector` existence, optionally requiring ancestor-aware visibility; `wait_for_network_idle` tracks an inflight requestId set from daemon-drained events, session-filtered, until an idle_ms gap.
**Invariant:** visibility is INHERITED (checkVisibility walks ancestors); idle detection must be scoped to the active session or background tabs defeat it; the daemon's global event buffer is drained wholesale, so the consumer filters.
**Probe:** `tests/unit/test_helpers.py:56` `test_page_info_raises_clear_error_on_js_exception` (adjacent); the waits are exercised in integration (`tests/integration/test_js.py`) — coverage caveat: no isolated unit test for the idle window.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "browser-harness", query: "wait_for_network_idle session filter inflight", limit: 10, fields: ["name","file","lines"] });
```

## Verdict
Adopt the three-wait taxonomy (each fixes one real SPA failure) and the session-scoped idle filter; adapt selectors/timeouts; omit nothing. Coverage caveat: idle window tested only in integration.
