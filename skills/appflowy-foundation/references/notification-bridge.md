<!-- capsule-v2 -->
# Notification bridge — how do async CRDT events become typed Dart notifications without unbounded buffering?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** How do document subscriptions forward block changes, sync state, and awareness to the UI, and what is the mpsc(1) pattern in the user-update path?

## subscribe_* + document_notification_builder
**Path/Symbol:** `frontend/rust-lib/flowy-document/src/document.rs` (`subscribe_document_changed` :9-40, `subscribe_document_snapshot_state` :42-58, `subscribe_document_sync_state` :60-74) + `af_cloud/server.rs:user_service` (:175-197).
**Signature:** `pub fn subscribe_document_changed(doc_id: &Uuid, document: &mut Document)`; notification builder `.payload::<DocEventPB>((events, is_remote, None).into()).send()`.
**Data Shape:** DocEventPB carries `(events, is_remote, source)` — the `is_remote` flag is how the UI distinguishes local edits from sync-applied ones.

### Decisive source
```rust
// document.rs :11-24 — callback closure clones id; payload includes is_remote
document.subscribe_block_changed("key", move |events, is_remote| {
  document_notification_builder(&doc_id_clone_for_block_changed,
    DocumentNotification::DidReceiveUpdate)
    .payload::<DocEventPB>((events, is_remote, None).into())
    .send();
});
// :43-57 — stream subscriptions run on a spawned task, not a callback
let mut snapshot_state = collab.subscribe_snapshot_state();
tokio::spawn(async move {
  while let Some(snapshot_state) = snapshot_state.next().await { ...send... }
});
```
```rust
// af_cloud/server.rs :176-190 — mpsc(1): latest-value backpressure for profile changes
let mut user_change = self.ws_client.subscribe_user_changed();
let (tx, rx) = tokio::sync::mpsc::channel(1);
tokio::spawn(async move {
  while let Ok(user_message) = user_change.recv().await {
    if let UserMessage::ProfileChange(change) = user_message {
      let _ = tx.send(user_update).await;   // blocks when UI is slow → natural coalescing
    }
  }
});
```

**Flow:** Block-change callbacks fire synchronously on the collab thread and build+send a notification immediately (id cloned into each closure); snapshot/sync-state streams are consumed by spawned tasks so slow UIs never block the collab. The user-profile channel is deliberately `mpsc::channel(1)`: while Dart is busy, sends await, collapsing bursts of profile changes into at-most-one-queued update.
**Invariant:** Notifications are fire-and-forget with per-recipient ids (doc_id as notification key); subscription wiring happens ONLY inside `create_document_instance` under `enable_sync=true`, so background reads produce zero UI noise.
**Probe:** Source-pinned byte-exact at HEAD (`subscribe_document_changed` :9-40, `user_service` channel(1)). Retrieval line-exact via `subscribe_document_changed DocumentNotification`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "subscribe_document_changed subscribe_document_sync_state notification", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt callback-vs-stream split and bounded-channel coalescing. Adapt PB types to your wire format. Omit awareness payloads if you don't render remote cursors.
