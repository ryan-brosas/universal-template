<!-- capsule-v2 -->
# Range-start-keyed model builder — turning an event stream into an immutable query façade

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you convert positional semantic events into an O(1)-query model WITHOUT keeping node pointers alive during construction?

## SemanticModelBuilder: parallel node walk + event replay → Arc'd index tables
**Path/Symbol:** `crates/biome_js_semantic/src/semantic_model/builder.rs` — `SemanticModelBuilder` fields (:17-38), `push_node` (:69-151), `push_event` (:159-413), `build` (:416-450), `resolve_global_name` (:452-465), `find_jsdoc` (:492-504); entry driver `semantic_model()` in `src/semantic_model.rs:58-86` (ONE preorder feeding BOTH `builder.push_node` and `extractor.enter`, then drains all events, then builds).
**Signature:** `push_node(&node)` indexes identifier-ish nodes by `text_trimmed_range().start()` and scope-ish nodes by full TextRange; `push_event(SemanticEvent)` folds events into typed vecs; `build(self) -> SemanticModel` wraps `SemanticModelData` in `Arc`.
**Data Shape:** Every lookup table is keyed by POSITION, not pointer: `binding_node_by_start: FxHashMap<TextSize, JsSyntaxNode>`, `bindings_by_start` / `declared_at_by_start: FxHashMap<TextSize, _>`, `scope_range_by_start` → converted at build into `rust_lapper::Lapper<u32, ScopeId>` interval tree; scopes/bindings live in dense `Vec`s addressed by `ScopeId(index+1)` / `BindingId(index)`.

### Decisive source
```rust
Read { range, declaration_at, scope_id } => {
    let binding_id = self.bindings_by_start[&declaration_at];   // events carry declaration_at ⇒ no search
    let reference_id = ReferenceId::new(binding_id, binding.references.len()); // (binding, index-in-vec) pair
    binding.references.push(SemanticModelReference { range_start: range.start(), ty: Read { hoisted: false } });
    let scope = &mut self.scopes[scope_id.index()];
    scope.read_references.push(reference_id);                    // NB: writes ALSO land in read_references
    if !self.is_svelte_store_assignment(range) {                 // flavor carve-out, see svelte-flavor-fallback.md
        self.declared_at_by_start.insert(range.start(), binding_id);
    }
}
UnresolvedReference { is_read, range } => /* name looked up in binding_node_by_start text;
    if configured global → global_references_by_start + lazily-created globals entry;
    else → unresolved_references vec + by-start set */
```

**Flow:** DeclarationFound allocates the next BindingId, records jsdoc (ancestor scan for JsExport/TsDeclareStatement/AnyJsDeclaration carrying a JSDoc comment), merges `TsBindingReference` unions into `scope.bindings_by_name` (keeping the PREVIOUS ref so same-name functions can form `overloads_by_name: SmallVec<[BindingId;2]>` — appended only when a Function follows a Function, deliberately allocation-free on the common unique-name path), and records hoisting in `scope_hoisted_to_by_range`. `build()` freezes everything behind Arc so returned `Scope`/`Binding`/`Reference` handles clone cheaply and outlive the model. Queries then compose: `model.binding(reference)` = one hashmap hit; `model.as_binding(node)` = direct index (panics if absent — caller guarantees a binding node); `all_calls(fn)` = fn's binding `.all_reads()` filtered by ancestor-walk to JS_CALL_EXPRESSION.
**Invariant:** Events MUST arrive in emission order (scopes strictly nested, declarations before their references' resolution) — the builder indexes `self.scopes[scope_id.index()]` with debug_asserts and would panic otherwise. The `read_references`-also-holds-writes quirk means closure iteration must merge BOTH vecs (see closure-capture-iterator.md); treating `read_references` as exclusive-reads silently drops captures.
**Probe:** `src/tests/format.rs` (insta snapshot of the rendered model), `src/tests/db.rs` salsa reuse tests exercise `build()` output equality; `semantic_model.rs` doc-test shows the canonical drive loop.
**Coverage caveat:** `overloads_by_name` merge path has no dedicated unit test at this pin (exercised indirectly by `tests/references.rs::ok_function_overloading`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "SemanticModelBuilder push_event bindings_by_start scope_range_by_start Lapper", limit: 10 });
```

## Verdict
Adopt the position-keyed two-phase design (index nodes during walk, fold events after) for any IDE-style model; adapt Lapper to your interval-index library; omit the globals registry if your host supplies environment symbols differently.
