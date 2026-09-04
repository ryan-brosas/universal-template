<!-- capsule-v2 -->
# Dependency composition root — in a crate graph with circular service needs, how do you wire managers without reference cycles or init deadlocks?

**Source:** AppFlowy AGPL-3.0 `main@5cf3a365dec0d59f64bad1ee4bb1050471a39b93`; Codebase Memory `ext-appflowy`. **Question:** What is the construction order inside `AppFlowyCore::init`, and why does everything take `Weak` while the core owns `Arc`?

## AppFlowyCore::init: single-owner Arc, everywhere-else Weak
**Path/Symbol:** `frontend/rust-lib/flowy-core/src/lib.rs:AppFlowyCore::init` (:124-332) + `module.rs:make_plugins`.
**Signature:** `async fn init(config: AppFlowyCoreConfig, runtime: Arc<AFPluginRuntime>) -> Self`; resolvers like `FolderDepsResolver::resolve(Arc::downgrade(&authenticate_user), collab_builder.clone(), Arc::downgrade(&server_provider), store_preference).await`.
**Data Shape:** Core struct fields are `Arc<...Manager>` (sole strong owners); every cross-manager dependency is `Weak` (`Arc::downgrade` at each call site), upgraded on demand into `FlowyError` on failure.

### Decisive source
```rust
// :187-247 — the wiring ORDER is load-bearing: storage → builder → folder → ai → database → document → user → search
let collab_builder = Arc::new(AppFlowyCollabBuilder::new(
  server_provider.clone(),
  WorkspaceCollabIntegrateImpl(Arc::downgrade(&authenticate_user)),
  instant_indexed_data_writer.as_ref().map(Arc::downgrade),
));
let folder_manager = FolderDepsResolver::resolve(...).await;
let database_manager = DatabaseDepsResolver::resolve(
  ..., task_dispatcher.clone(), Arc::downgrade(&collab_builder), ...).await;
let document_manager = DocumentDepsResolver::resolve(...);
let user_manager = UserDepsResolver::resolve(...,
  Arc::downgrade(&database_manager), Arc::downgrade(&folder_manager)).await;
```
```rust
// :295-300 + :302-314 — user init BEFORE dispatcher exists; dispatcher built LAST
if let Err(err) = user_manager.init_with_callback(app_life_cycle, collab_interact_impl).await {
  error!("Init user failed: {}", err) }
let event_dispatcher = Arc::new(AFPluginDispatcher::new(runtime,
  make_plugins(Arc::downgrade(&folder_manager), ...)));
```

**Flow:** TaskDispatcher spawns its runner first; storage/builder/folder/ai/database/document/user/search managers resolve in dependency order inside ONE async block; `register_handlers` wires cross-folder callbacks; the app-lifecycle struct (all Weak) is handed to `user_manager.init_with_callback` so sign-in/out events fan out to every manager; only then does `make_plugins` assemble the AFPlugin list and the dispatcher come into existence. The task scheduler timeout is 10s (`TaskDispatcher::new(Duration::from_secs(10))`).
**Invariant:** Exactly one strong reference per manager lives in `AppFlowyCore`; any manager→manager edge is Weak so Drop order can never deadlock or leak cycles; the event dispatcher is constructed AFTER user init because plugin handlers capture Weak handles that assume initialized state. A porter who "simplifies" a Weak to Arc here creates a drop-order deadlock that only manifests at logout.
**Probe:** Source-pinned byte-exact at HEAD (`AppFlowyCore::init` :124-332). Retrieval rank#1 line-exact for `make_plugins` composition; coverage stdin-JSON 19 cited paths all no_recorded_issue+metadata_match generation_matches=true.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-appflowy", query: "AppFlowyCore init make_plugins deps_resolve downgrade", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt single-strong-owner + Weak-everywhere composition and the explicit resolver ordering. Adapt manager set to your feature surface. Omit profiling/console-subscriber branches.
