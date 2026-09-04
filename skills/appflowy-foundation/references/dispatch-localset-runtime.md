<!-- capsule-v2 -->
# LocalSet dispatch runtime — why does async_send panic outside a LocalSet, and how do panicking handlers become JoinError responses?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What execution contexts can legally call the dispatcher under default features, and what happens to a handler that panics or to the dispatcher when its runtime drops?

## spawn_local + JoinError laundering
**Path/Symbol:** `frontend/rust-lib/lib-dispatch/src/dispatcher.rs:AFPluginDispatcher.boxed_async_send_with_callback` (:99-131, `#[cfg(feature = "local_set")]`) + `runtime.rs:AFPluginRuntime` (:23-77) + `dart-ffi/src/lib.rs:Runner` (:189-228).
**Signature:** `pub async fn boxed_async_send_with_callback<Req, Callback>(dispatch: &AFPluginDispatcher, request: Req, callback: Callback) -> AFPluginEventResponse`; `AFConcurrent: Send` (local_set) vs `Send + Sync` otherwise.
**Data Shape:** `local_set` is in DEFAULT features (`lib-dispatch/Cargo.toml [features] default = ["local_set", "use_protobuf"]`); futures are `LocalBoxFuture`, handlers need only `Send`, not `Sync`.

### Decisive source
```rust
// dispatcher.rs :117-130 — local_set flavor runs on the CALLING thread's LocalSet
let result = tokio::task::spawn_local(async move {
  service.call(service_ctx).await.unwrap_or_else(|e| { ... })
}).await;
result.unwrap_or_else(|e| {
  let msg = format!("EVENT_DISPATCH join error: {:?}", e);
  tracing::error!("{}", msg);
  let error = InternalError::JoinError(msg);
  error.as_response()
})
```
```rust
// dart-ffi/src/lib.rs :160-163 — production host: ONE dedicated OS thread owns a LocalSet
let handle = std::thread::spawn(move || {
  let local_set = LocalSet::new();
  cloned_runtime.block_on(local_set.run_until(Runner { rx: task_rx }));
});
```

**Flow:** Production: dart-ffi's `init_sdk` spawns a dedicated thread running `LocalSet::run_until(Runner)`; every FFI event becomes a Task on an unbounded mpsc; `Runner::poll` drains it with `tokio::task::spawn_local`, so all handlers execute on that single thread — no `Sync` bounds needed anywhere. A handler PANIC is caught by the JoinHandle of `spawn_local` and laundered into an `InternalError::JoinError("EVENT_DISPATCH join error: ...")` response delivered through the callback port. The dispatcher embeds its own multi-thread `AFPluginRuntime` for background spawns; dropping that runtime inside an async context panics, which is why lib-dispatch's own test ends with `std::mem::forget(dispatch)` and why DartAppFlowyCore keeps it in an `Arc`.
**Invariant:** Under default features `async_send*` MUST run inside a LocalSet (`spawn_local` panics otherwise — verified live); handler panics never cross the FFI boundary as panics, only as error responses; the embedded runtime outlives all dispatched futures (forget/Arc discipline).
**Probe:** `/tmp/extcollab-af-probe` t02/t03/t04/t05 executed inside `LocalSet::run_until` — GREEN; first RED run proved bare `#[tokio::test]` context panics at `spawn_local`. Upstream `cargo test -p lib-infra` BLOCKED at this pin (dev-deps missing tokio macros/rt features).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "boxed_async_send_with_callback spawn_local LocalSet", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the dedicated-thread LocalSet host pattern for FFI boundaries where handlers are !Sync. Adapt thread count/runtime flavor if you enable non-local_set builds (then futures must be Send+boxed). Omit the wasm branch.
