<!-- capsule-v2 -->
# Infer-type deferred binding + bogus-conditional fallback flush

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** Where do `infer T` type parameters live when their owning scope doesn't exist yet at sighting time — and what happens if that scope never parses?

## infers stash → push_infers_in_scope on the true-branch, with leave-side FALLBACK
**Path/Symbol:** `crates/biome_js_semantic/src/events.rs` — extractor field `infers: Vec<TsTypeParameterName>` (:163), early-return deferral in `enter_identifier_binding` TsInferType arm (:774-780), `enter_any_type` conditional-true-branch scope+flush (:508-521), `leave_any_type` pop + FALLBACK (:1001-1023), `push_infers_in_scope` (:1053-1071).
**Signature:** `push_infers_in_scope()` does `mem::take(&mut self.infers)` then registers each name as `BindingName::Type` with kind TS_INFER_TYPE, emitting DeclarationFound{declaration_kind: Generic} in the CURRENT scope; the take means each batch fires exactly once.
**Data Shape:** Deferred items are bare syntax nodes (TsTypeParameterName); no BindingInfo is created until flush.

### Decisive source
```rust
AnyJsBindingDeclaration::TsInferType(_) => {
    // Delay the declaration of parameter types that are inferred.
    // Their scope corresponds to the true branch of the conditional type.
    self.infers.push(TsTypeParameterName::unwrap_cast(node.syntax().clone()));
    return;                                   // NO DeclarationFound yet — scope not entered
}
// leave side:
if matches!(node.kind(), JsSyntaxKind::TS_CONDITIONAL_TYPE) && !self.infers.is_empty() {
    self.push_infers_in_scope()   // FALLBACK: bogus/missing true-branch ⇒ bind in the
}                                 // conditional's OWN scope so every declaration gets one
```

**Flow:** Happy path: `T extends U ? T2 infer… `— entering the TRUE branch of TsConditionalType pushes a dedicated strict-mode scope and immediately flushes all stashed infers into it; leaving pops them together. Failure path: if error recovery mangled the conditional so the true branch never ENTERED as a scope-bearing node, the LEAVE of TsConditionalType finds a non-empty `infers` stash and binds everything in the enclosing (conditional's) scope instead. Either way the invariant "every declaration found ⇒ has a binding" holds.
**Invariant:** The flush is consume-once (`mem::take`) — leftover infers can only mean the fallback fired. Scope choice differs by path (true-branch scope vs conditional scope), so consumers must NOT hardcode "infers live in their own scope". This mirrors the parser's own RecoveryDisabled philosophy from earlier passes: degrade loudly-but-safely rather than lose declarations.
**Probe:** `src/tests/scopes.rs::ok_type_parameter*` family (START/END around type-parameter scopes with `/*# Event */` declaration assertions inside template literals); `tests/infer.rs`; `src/tests/references.rs::ok_typescript_type_parameter_name` (mapped-type `[key in P]` read-back).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "push_infers_in_scope TsInferType in_conditional_true_type TS_CONDITIONAL_TYPE mem::take", limit: 10 });
```

## Verdict
Adopt the stash-and-flush-with-fallback pattern for any construct whose owning scope may fail to materialize under error recovery; adapt the trigger node kinds; omit nothing — the fallback IS the lesson.
