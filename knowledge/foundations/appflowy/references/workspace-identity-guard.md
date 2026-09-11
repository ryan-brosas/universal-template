<!-- capsule-v2 -->
# Workspace-scoped collab identity — how do you prevent a stale async task from writing into a workspace the user already left?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** Why does every collab construction re-check the CURRENT workspace id against the requested one, and what exactly does it compare?

## collab_object workspace guard + device identity
**Path/Symbol:** `frontend/rust-lib/collab-integrate/src/collab_builder.rs:AppFlowyCollabBuilder.collab_object` (:126-151) + `WorkspaceCollabIntegrate` trait (:71-74).
**Signature:** `pub fn collab_object(&self, workspace_id: &Uuid, uid: i64, object_id: &Uuid, collab_type: CollabType) -> Result<CollabObject, Error>`; `trait WorkspaceCollabIntegrate { fn workspace_id(&self) -> Result<Uuid, FlowyError>; fn device_id(&self) -> Result<String, FlowyError>; }`.
**Data Shape:** `CollabObject::new(uid, object_id.to_string(), collab_type, workspace_id.to_string(), device_id)` — the tuple that keys persistence AND cloud routing for the object's whole life.

### Decisive source
```rust
// :133-142 — the comment IS the invariant
let actual_workspace_id = self.workspace_integrate.workspace_id()?;
if workspace_id != &actual_workspace_id {
  return Err(anyhow::anyhow!(
    "workspace_id not match when build collab. expect workspace_id: {}, actual workspace_id: {}",
    workspace_id, actual_workspace_id));
}
```

**Flow:** Every manager resolves its target `(workspace_id, object_id)` up front and passes it through; at BUILD time the builder re-reads the live session's workspace id from `WorkspaceCollabIntegrate` (backed by AuthenticateUser) and refuses on mismatch. The resulting CollabObject then flows into RocksDB namespacing (`(uid, workspace_id, object_id)` keys), plugin attachment, and cloud sync calls.
**Invariant:** A document can never be constructed into the wrong workspace's storage namespace even when its open request was queued before a workspace switch completed — the check is at the LAST moment before any disk or network write. Device id participates in sync identity (empty device ids are replaced with fresh UUIDs at server construction, af_cloud/server.rs:71-75).
**Probe:** Source-pinned byte-exact at HEAD (`collab_object` :126-151). Retrieval rank#1 via "finalize AppFlowyCollabBuilder" (same impl block); coverage metadata_match.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "collab_object workspace_id not match build collab", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt last-moment tenant/workspace validation before any persisted write. Adapt the session-integrate trait to your auth layer. Omit nothing — this guard is 10 lines and prevents cross-workspace corruption.
