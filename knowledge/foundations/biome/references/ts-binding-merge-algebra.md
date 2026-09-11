<!-- capsule-v2 -->
# TsBindingReference merge algebra — one name, up to three slots, folded in place

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you model TypeScript declaration merging (interface + const + namespace sharing ONE name) inside a flat per-scope map?

## Five-variant reference + 20-arm union_with lattice
**Path/Symbol:** `crates/biome_js_semantic/src/semantic_model/binding.rs` — `enum TsBindingReference` (:198-214: Type(BindingId), ValueType(BindingId), TypeAndValueType(BindingId), NamespaceAndValueType(BindingId), Merged{ty,value_ty,namespace_ty: Option<BindingId>}), `from_binding_and_declaration_kind` (:218-232), `namespace_ty_or_ty` (:237-247), `value_ty_or_ty` (:251-266), `union_with(self, other)` (:274-460, graph-resolved 274-460); consumer `SemanticModelBuilder.push_event` Entry::Occupied arm (builder.rs :248-258); scope storage `bindings_by_name: FxHashMap<TokenText, TsBindingReference>` (scope.rs :20) + separate `overloads_by_name` (:24).
**Signature:** `union_with` folds the NEW binding into the EXISTING slot entry at declaration time; getters resolve with priority — namespace-or-type for type queries, value-or-namespace-or-type for value queries (`get_binding(name)` returns `value_ty_or_ty()`).
**Data Shape:** Single-slot variants exist for the common case (zero extra allocation); `Merged` appears only when ≥2 distinct bindings share a name. Overloads deliberately do NOT live here: two same-name Functions merge last-wins through the normal path while their ids accumulate in `overloads_by_name: SmallVec<[BindingId;2]>`.

### Decisive source
```rust
(Self::Type(own), Self::ValueType(other)) => {
    if own == other { Self::TypeAndValueType(other) }          // same node declaring both
    else { Self::Merged { ty: Some(own), value_ty: Some(other), namespace_ty: None } } // true merging
}
(Self::Type(own), Self::NamespaceAndValueType(other)) =>
    Self::Merged { ty: Some(own), value_ty: Some(other), namespace_ty: Some(other) }
/* …20 arms total; final catch-all `(_, other) => other` makes later declarations win
   for any unlisted combination; Merged+Merged folds field-wise via .or() */
```

**Flow:** Builder inserts `TsBindingReference::from_binding_and_declaration_kind(binding_id, kind)` on first sight of a name; on collision it stores `previous.union_with(new)` and KEEPS `previous` to decide overload-set membership (Function-follows-Function). Queries pick a getter per need: type position → `namespace_ty_or_ty()`, value position → `value_ty_or_ty()`; both fall back down a fixed preference chain so merged names still answer.
**Invariant:** Same-id Type+ValueType COLLAPSES into TypeAndValueType (dedup); different-id pairs must NOT collapse or you lose which binding answers which query. The lattice is order-sensitive only through the catch-all — listed arms are symmetric; porters adding kinds MUST extend every interacting arm or silently hit `(_, other) => other` last-wins.
**Probe:** `src/tests/references.rs::ok_function_overloading` / `ok_function_overloading_2`; `tests/db.rs::added_export_is_not_eq` pins that exported-set changes matter to equality; no dedicated unit test for union_with itself — coverage caveat (behavior pinned indirectly via module-graph consumers).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "TsBindingReference union_with Merged namespace_ty value_ty bindings_by_name", limit: 10 });
```

## Verdict
Adopt the slot-variant + fold-in-place design for multi-namespace name resolution; adapt variant set to your namespaces; omit overloads_by_name if your host has no function overloading.
