<!-- capsule-v2 -->
# Scope-stack reference resolution — references resolve at scope POP, not at sighting

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does a single-pass pre-order walk produce correct binding↔reference links without a fixpoint or symbol table?

## SemanticEventExtractor: defer every reference to pop_scope
**Path/Symbol:** `crates/biome_js_semantic/src/events.rs` — `SemanticEvent` enum (:23-101, 9 variants), `SemanticEventExtractor` state (:152-166: `stash: VecDeque`, `scopes: Vec<Scope>`, `bindings: FxHashMap<BindingName, BindingInfo>` FLAT map, `infers`, `is_ambient_context`), `enter`/`leave` kind dispatch (:308-506/:934-999), `push_binding` (:1361-1384), `pop_scope` (:1101-1171, graph-resolved 1101-1171), `resolve_references_in_scope` (:1179-1275), `resolve_references_in_dual_scope` (:1277-1325).
**Signature:** push-driven API — caller feeds `enter(node)` on WalkEvent::Enter and `leave(node)` on Leave in ONE pre-order, draining `pop()` until None after each step (or use `semantic_events(root)` iterator wrapper :1408-1463).
**Data Shape:** Per-scope: `bindings: Vec<BindingName>` (declared here), `references: FxHashMap<BindingName, Vec<Reference>>` (unresolved, waiting), `shadowed: Vec<(BindingName, BindingInfo)>` (occluded outers to restore). The GLOBAL `self.bindings` map holds only currently-visible bindings; `BindingInfo{range_start, declaration_kind}` — just enough to emit `declaration_at`.

### Decisive source
```rust
fn pop_scope(&mut self, scope_range: TextRange) {
    let scope = self.scopes.pop().unwrap();
    for (name, mut references) in scope.references {          // everything seen inside, now resolvable
        if let Some(info) = self.bindings.get(&name).cloned() { self.resolve_references_in_scope(name, references, &info, scope_id); continue; }
        if let Some(info) = self.bindings.get(&name.clone().dual()).cloned() { self.resolve_references_in_dual_scope(name, references, &info); continue; }
        /* svelte fallback */
        if let Some(parent) = self.scopes.last_mut() { parent.references.entry(name).or_default().append(&mut references); }  // PROMOTE upward
        else { for r in references { stash.push_back(UnresolvedReference { is_read: !r.is_write(), range: r.range() }); } }
    }
    for b in scope.bindings { self.bindings.remove(&b); }     // unbind
    self.bindings.extend(scope.shadowed);                     // restore occluded outers
}
```

**Flow:** enter pushes a scope for each scope-introducing kind (root kinds + functions/arrows/methods as closures + class/enum/TS-signature scopes implying strict mode + block/for/switch/catch with `HoistDeclarationsToParent`); identifiers register bindings immediately (see js-declaration-kind-ladder.md) and references are merely QUEUED under their name. At leave, the popped scope resolves queued refs against the flat visible-binding map; misses promote to the parent scope and retry there; a miss at global scope becomes `UnresolvedReference`. Shadowing is handled by save-and-restore around each scope lifetime.
**Invariant:** Resolution ORDER is innermost-first because promotion re-queues into the parent BEFORE it pops — so a name bound anywhere on the ancestor chain wins at the deepest scope that has it, exactly JS scoping. Read vs HoistedRead is decided ONLY at resolution time by comparing `declaration_at < reference.range.start()` — never at sighting. The dual lookup (`Type`↔`Value` via `BindingName::dual()`) is what lets `typeof X` find a value-only binding while `let x: X` finds the type twin.
**Probe:** `src/tests/scopes.rs` (START/END comment assertions pin exact scope ranges incl. for-head-vs-body double scopes and catch-clause scope B1/B2 nesting), `src/tests/references.rs::ok_reference_switch` (case clauses share one scope until an explicit `{}`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "pop_scope resolve_references_in_scope shadowed BindingName dual stash", limit: 10 });
```

## Verdict
Adopt the queue-at-sight/resolve-at-pop algorithm verbatim for any lexical resolver; adapt event vocabulary to your IR; omit the dual-name machinery if your language has no type/value namespace split (then delete `resolve_references_in_dual_scope`).
