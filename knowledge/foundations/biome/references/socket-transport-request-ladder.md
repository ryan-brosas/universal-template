<!-- capsule-v2 -->
# Socket transport request ladder — how does a blocking client multiplex requests over one connection?

**Source:** biome MIT `main@88f805e19b67ab4c876e4fc4a8b4018bd03df20b`; Codebase Memory `biome`. **Question:** How do you block a synchronous caller per request while a background task demultiplexes responses by id?

## Pending-map + oneshot + bounded select
**Path/Symbol:** `crates/biome_cli/src/service/mod.rs:` `SocketTransport` (:104-108), `PendingRequests` (:112-137), `open` (:140-182), `impl WorkspaceTransport for SocketTransport` (:188-246).
**Signature:** `fn request<P, R>(&self, request: TransportRequest<P>) -> Result<R, TransportError> where P: Serialize, R: DeserializeOwned`.
**Data Shape:** `write_send: Sender<(Vec<u8>, bool)>` — the bool is an `is_shutdown` flag riding each queued message; `pending_requests: PendingRequests` wraps `Arc<papaya::HashMap<u64, Mutex<Option<oneshot::Sender<Result<Box<RawValue>, TransportError>>>>>>`.

### Decisive source
```rust
let (send, recv) = oneshot::channel();
self.pending_requests.pin().insert(request.id, Mutex::new(Some(send)));
let is_shutdown = request.method == "biome/shutdown";
// ... serialize to JsonRpcRequest { jsonrpc: "2.0", id, method, params } ...
let response = self.runtime.block_on(async move {
    self.write_send.send((request, is_shutdown)).await
        .map_err(|_| TransportError::ChannelClosed)?;
    tokio::select! {
        result = recv => { /* Ok(Ok)/Ok(Err)/Err(_) => ChannelClosed */ }
        _ = sleep(Duration::from_secs(15)) => Err(TransportError::Timeout)
    }
})?;
```

**Flow:** register oneshot in the pending map BEFORE serializing → enqueue serialized bytes (bounded(16) channel; its doc says this is a *loose rate-limit*, not an in-flight cap) → block the calling thread until the read task fulfills the oneshot, a 15s timeout fires, or either side drops (mapped to `ChannelClosed`). The read task removes by response id and takes the sender (`ch.lock().ok()?.take()`), so late/duplicate responses find nothing.
**Invariant:** `PendingRequests::drop` calls `inner.pin().clear()`. Its doc comment carries the soundness argument: there are exactly two handles (transport + read task); the transport can only be dropped while no request is in flight (because `&self request` blocks), so clearing only ever cancels requests orphaned by a read-task abort — they fail fast instead of burning 15s timeouts. Shutdown is data, not a control channel: the `"biome/shutdown"` method name flips the tuple flag so `write_task` broadcasts and exits AFTER writing that final message.
**Probe:** upstream has no unit test for `request` itself (recorded caveat); adjacent daemon-hygiene tests exist at `crates/biome_cli/src/service/unix.rs` `mod tests` (:296+); compile gate `cargo check -p biome_cli --lib` exit 0 executed at pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SocketTransport request pending oneshot timeout shutdown write channel", limit: 10, fields: ["signature", "lines"] });
```
Observed GREEN retrieval at pin: `SocketTransport.request` Method :189-245 line-exact; `open_transport` :59-65.

## Verdict
Adopt id-keyed pending map + per-request oneshot + select-with-deadline as the blocking-over-async bridge, and the Drop-clears-pending cancellation argument; adapt the timeout constant and the bounded-write-channel policy to your workload; omit the LSP-flavored `is_shutdown` tuple hack if your protocol has real control frames. Coverage: service/mod.rs `no_recorded_issue`/`generation_matches` at pin; source read whole (486L).
