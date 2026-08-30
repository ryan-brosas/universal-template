<!-- capsule-v2 -->
# Instant indexing writer — how do you feed a search index from live CRDTs without blocking edits or leaking dead documents?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** How does the 30-second Weak-based reaper loop decide which documents to index, re-index, and forget?

## InstantIndexedDataWriter: Weak registry + ticker sweep
**Path/Symbol:** `frontend/rust-lib/collab-integrate/src/instant_indexed_data_provider.rs:InstantIndexedDataWriter` (`spawn_instant_indexed_provider` :69-170, `queue_collab_embed` :226-243) + `unindexed_data_form_collab` (:246-259).
**Signature:** `pub async fn spawn_instant_indexed_provider(&self, runtime: &Runtime) -> FlowyResult<()>`; `WriteObject { collab_object: CollabObject, collab: Weak<dyn CollabIndexedData> }`.
**Data Shape:** Registry = `Arc<RwLock<HashMap<object_id, WriteObject>>>`; consumers = `Vec<Box<dyn InstantIndexedDataConsumer>>`; supported type gate: `matches!(t, CollabType::Document)` ONLY (:172-174).

### Decisive source
```rust
// :74-89 — the loop's LIFETIME is bound to the registries via Weak; first tick consumed instantly
runtime.spawn(async move {
  let mut ticker = interval(interval_dur);   // 30s
  ticker.tick().await;                        // interval() fires immediately — swallow it
  loop {
    ticker.tick().await;
    let collab_by_object = match weak_collab_by_object.upgrade() {
      Some(m) => m, None => break,            // provider dropped → loop exits
    };
```
```rust
// :100-163 — per object: upgrade Weak (dead ⇒ collect), read paragraphs, fan out, then batch-remove
match guard.get(&id) {
  Some(wo) => match wo.collab.upgrade() {
    Some(collab_rc) => { let data = collab_rc.get_unindexed_data(&wo.collab_object.collab_type).await;
                         for consumer in consumers_guard.iter() { ...consume_collab... } },
    None => to_remove.push(id), },
  None => continue,
}
...
guard.retain(|k, _| !to_remove.contains(k));
```

**Flow:** `finalize()` in the collab builder queues every created document (Weak, so no ownership). Every 30s the sweeper snapshots keys under a read lock, for each live collab extracts `DocumentBody::paragraphs` inside `try_transact`, and calls EVERY consumer with `Option<UnindexedData>` (None data is still delivered — consumers decide). Dead Weak handles are collected and removed in ONE write-lock pass after the sweep. Errors from a consumer are logged and do NOT remove the entry — it retries next tick.
**Invariant:** The writer never keeps documents alive (Weak everywhere) and never blocks editors (read-lock + `try_read`/`try_transact` only — a busy doc is skipped this round); consumer failures retry indefinitely via the next tick. First-interval tick must be swallowed or the "30s" cadence fires immediately at startup.
**Probe:** Source-pinned byte-exact at HEAD (`spawn_instant_indexed_provider` :74-167, `queue_collab_embed` :226-243). Retrieval rank#1 line-exact on `InstantIndexedDataWriter spawn_instant_indexed_provider queue_collab_embed`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "InstantIndexedDataWriter spawn_instant_indexed_provider queue_collab_embed", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the Weak-registry + periodic-reaper pattern for derived indexes over live objects. Adapt interval and paragraph extraction to your block model. Omit the desktop-only gating (`is_desktop()`) unless you share mobile constraints.
