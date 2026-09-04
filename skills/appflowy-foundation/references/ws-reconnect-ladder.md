<!-- capsule-v2 -->
# WebSocket reconnect ladder — how do you reconnect a realtime client without thundering-herd and re-auth without tight loops?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** Which socket/token states trigger which recovery action, and how are overlapping reconnect attempts cancelled?

## spawn_ws_conn + attempt_reconnect
**Path/Symbol:** `frontend/rust-lib/flowy-server/src/af_cloud/server.rs:spawn_ws_conn` (:286-346) + `attempt_reconnect` (:354-380).
**Signature:** `async fn attempt_reconnect(ws_client: &Arc<WSClient>, minimum_delay_in_secs: u64, cancellation_token: &Arc<ArcSwap<CancellationToken>>) -> JoinHandle<()>`.
**Data Shape:** Two independent watch receivers drive the ladder: `ConnectState` (socket health) and `TokenState::{Refresh, Invalid}` (auth); `enable_sync: Arc<AtomicBool>` gates ALL reconnection.

### Decisive source
```rust
// :305-320 — state-driven reactions
ConnectState::PingTimeout | ConnectState::Lost => {
  if weak_api_client.upgrade().is_some() && enable_sync.load(Ordering::SeqCst) {
    attempt_reconnect(&ws_client, 2, &cloned_cancellation_token).await; } },
ConnectState::Unauthorized => {
  if let Err(err) = api_client.refresh_token("websocket connect unauthorized").await { ... } }
// :332-344 — token-driven reactions
TokenState::Refresh => attempt_reconnect(&ws_client, 5, &cancellation_token).await,
TokenState::Invalid => ws_client.disconnect().await,
```
```rust
// :359-363 — cancel-then-replace token + JITTERED delay capped at [min..10) seconds
cancellation_token.load_full().cancel();
let new_cancel_token = CancellationToken::new();
cancellation_token.store(Arc::new(new_cancel_token.clone()));
let delay_seconds = rand::thread_rng().gen_range(minimum_delay_in_secs..10);
tokio::spawn(async move { select! {
  _ = new_cancel_token.cancelled() => tracing::trace!("🟢 websocket reconnection attempt cancelled."),
  _ = tokio::time::sleep(Duration::from_secs(delay_seconds)) => { ws_client_clone.connect().await ... }
}})
```

**Flow:** Socket states `PingTimeout|Lost` → jittered reconnect (min 2s); `Unauthorized` → token refresh ONLY (no immediate reconnect — the resulting TokenState::Refresh event drives it). Token `Refresh` → reconnect with min 5s (fresh auth needs a fresh socket); `Invalid` → hard disconnect. Each `attempt_reconnect` cancels the PREVIOUS pending attempt via the ArcSwap'd token, swaps in a new one, sleeps a random `[min,10)` seconds, then connects.
**Invariant:** At most ONE reconnect sleep is ever in flight (cancel-before-store on the shared ArcSwap); sync disabled ⇒ no automatic reconnection at all; delays are randomized to prevent herd effects. Note `gen_range(min..10)` PANICS if min ≥ 10 — callers must pass min < 10.
**Probe:** `/tmp/extcollab-af-probe` battery covers adjacent kernels; this seam pinned byte-exact at HEAD (`spawn_ws_conn`, `attempt_reconnect`). Adversarial retrieval check: same query on ext-joplin/ext-docmost/ext-meetily returns total:0.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "attempt_reconnect CancellationToken rand gen_range thundering herd", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the state→action table and cancel-then-jitter reconnect. Adapt the WS library and token store. Omit the ArcSwap gymnastics if your runtime serializes reconnect attempts for you.
