<!-- capsule-v2 -->
# Generation-guarded module graph — ordering a data write against an incremental engine's cache invalidation

**Source:** biome MIT `main@88f805e19b67`; Codebase Memory `biome`. **Question:** When a bulk collection lives OUTSIDE the memoizer but queries over it are memoized, how do you order writes so no reader can cache new data under an old dependency version?

## write_module_data choreography + read-side generation pinning
**Path/Symbol:** `crates/biome_service/src/db/mod.rs:300-316` (`write_module_data`), `:859-881` (`ModuleDb for WorkspaceDb`: `module_graph_generation`, `module_for_path`, `for_each_module`).
**Signature:** `fn write_module_data(&mut self, write: impl FnOnce(&HashMap<Utf8PathBuf, ModuleInfo>))`; `u64` generation via `wrapping_add(1)`.

### Decisive source
```rust
// :306-315 — salsa write STARTS before the mutation, generation setter COMPLETES after it
fn write_module_data(&mut self, write: impl FnOnce(&HashMap<Utf8PathBuf, ModuleInfo>)) {
    let generation = ModuleGraphGeneration::get(self);
    let next = generation.value(self).wrapping_add(1);
    let modules = self.modules.clone();
    let pending_setter = generation.set_value(self); // opens the write
    write(&modules);                                 // mutate shared map
    pending_setter.to(next);                         // close it at the NEW generation
}
// :866-869 — readers MUST read the generation first so the engine tracks the dependency
fn module_for_path(&self, path: &Utf8Path) -> Option<ModuleInfo> {
    let _ = self.module_graph_generation();
    self.get_module(path)
}
```

**Flow:** writer opens the generation setter (salsa marks the query dirty) → mutates the papaya map → completes the setter with generation+1 → any query that previously read the old generation value re-runs. Reader: touch `module_graph_generation()` BEFORE reading map data so its memoized result depends on the generation it observed.
**Invariant:** A read can never observe new map contents while still recording the OLD generation as its dependency — that would freeze stale results until an unrelated bump. The untracked escape hatch exists for control flow only: `contains_module_untracked` (:246-255) is documented "Do not use it in a Salsa query or before reading module data". `wrapping_add` makes overflow a correctness-preserving non-issue (any change invalidates).
**Probe:** `grep -n 'pending_setter.to(next)' crates/biome_service/src/db/mod.rs` → `:315`; `grep -n 'wrapping_add(1)' crates/biome_service/src/db/mod.rs` → 3 hits: production `:308`, plus test assertions `:2041`/`:2081` pinning the same arithmetic; `grep -n 'let _ = self.module_graph_generation();' crates/biome_service/src/db/mod.rs` → `:868` AND `:874` (both ModuleDb readers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "write_module_data module_graph_generation ModuleDb", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: open-write/mutate/close-generation ordering plus mandatory pre-read of the version counter in every memoized accessor; expose an explicitly UNTRACKED contains-check for control flow only. Adapt to any memoization framework with dependency tracking (build systems, incremental compilers). Omit the Rc<dyn ModuleDb> plumbing.
