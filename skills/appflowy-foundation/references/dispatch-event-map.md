<!-- capsule-v2 -->
# Event-map dispatch kernel — how do you route typed events to exactly one handler with a failure-isolated response contract?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** How does `AFPluginDispatcher` guarantee one-handler-per-event, and what is the complete error taxonomy a caller can receive as a response instead of a panic?

## Plugin map construction + DispatchService
**Path/Symbol:** `frontend/rust-lib/lib-dispatch/src/module/module.rs:plugin_map_or_crash` (:28-47), `AFPlugin::event` (:107-125); `frontend/rust-lib/lib-dispatch/src/dispatcher.rs:DispatchService::call` (:247-290).
**Signature:** `fn plugin_map_or_crash(plugins: Vec<AFPlugin>) -> AFPluginMap` (=`Arc<HashMap<AFPluginEvent, Arc<AFPlugin>>>`); `AFPluginEvent(String)` newtype built from any `Display+Eq+Hash` type.
**Data Shape:** Request = `{id: nanoid!(6), event, payload: Payload::{None,Bytes}}`; response = `AFPluginEventResponse{status_code, payload}` where error bodies carry human-readable strings.

### Decisive source
```rust
// module.rs :34-43 — duplicate event across plugins = panic at STARTUP, not dispatch time
events.into_iter().for_each(|e| {
  if plugin_map.contains_key(&e) {
    let plugin_name = plugin_map.get(&e).map(|p| &p.name);
    panic!("⚠️⚠️⚠️Error: {:?} is already defined in {:?}", &e, plugin_name);
  }
  plugin_map.insert(e, plugins.clone());
});
// dispatcher.rs :274-277 — missing handler at DISPATCH time is an ERROR RESPONSE
None => {
  let msg = format!("[dispatch]: can not find the event handler. {:?}", request);
  Err(InternalError::HandleNotFound(msg).into())
}
```
```rust
// dispatcher.rs :282-288 — every failure becomes a response; callback still runs
let response = result.unwrap_or_else(|e| e.into());
if let Some(callback) = callback { callback(response.clone()).await; }
Ok(response)
```

**Flow:** Build time: every event of every plugin lands in ONE flat map keyed by the stringified event — duplicates PANIC immediately (`AFPlugin::event` re-checks within a plugin). Dispatch: `DispatchService.call` looks up the map → factory → service → handler future; ANY error (handler error, extraction error, `ServiceNotFound`, `HandleNotFound`) converts into an `AFPluginEventResponse` via the `Error::as_response` trait object inside `DispatchError`; the optional callback receives success AND failure responses.
**Invariant:** Exactly one handler per event, enforced by startup panic; the dispatcher NEVER returns Err to its caller — errors are data in the response body ("can not find the event handler", "Can not find service factory for event", JoinError text). This response-as-error-channel is what lets Dart FFI callers treat every outcome uniformly.
**Probe:** `/tmp/extcollab-af-probe` t01 (duplicate panics), t02 (unknown-event body contains "can not find the event handler"), t05 (panic → "EVENT_DISPATCH join error" body) — all executed GREEN against lib-dispatch at this pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "AFPluginDispatcher DispatchService call module_map", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt flat-string event routing with fail-fast duplicate detection and total error→response conversion. Adapt the event key type (any Display enum works) and callback plumbing. Omit the protobuf payload codec (feature-gated) if your host uses JSON/flatbuffers.
