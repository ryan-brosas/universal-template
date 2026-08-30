<!-- capsule-v2 -->
# Hoisting-target scope search — var/function/class land where JS says, found by stack walk

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How does one walk compute the correct hoist target for var-inside-block, function declarations, AND class/enum names without per-kind special cases?

## scope_index_to_hoist_declarations: skip-N then first non-hoisting scope
**Path/Symbol:** `crates/biome_js_semantic/src/events.rs` — `scope_index_to_hoist_declarations(skip)` (:1343-1358), `ScopeHoisting::{DontHoistDeclarationsToParent, HoistDeclarationsToParent}` (:275-279) stamped per scope in `push_scope` (:1073-1094), call sites in `enter_identifier_binding` (:541-810).
**Signature:** `fn scope_index_to_hoist_declarations(&mut self, skip: u32) -> Option<ScopeId>` — reverse-iterate `self.scopes`, skip `skip` entries, return the FIRST scope whose hoisting is DontHoist…, filtered to exclude the current scope itself (`.filter(|id| current != *id)` ⇒ None means "stay local").
**Data Shape:** `DeclarationFound { scope_id, hoisted_scope_id: Option<ScopeId>, … }` carries BOTH ids; the builder stores the binding under `hoisted_scope_id.unwrap_or(scope_id)` and separately records `scope_hoisted_to_by_range[range.start()] = hoisted_scope_id` so queries can ask "was THIS binding hoisted?".

### Decisive source
```rust
// skip=0 → var / binding-pattern-in-var: nearest function-ish boundary
//   function f() { if (true) { var a; } }        → a lands in f's scope
// skip=1 → function declarations: jump over own body scope
//   strict-mode variant uses scopes.iter().rev().nth(1) DIRECTLY (sloppy-mode annex-B
//   semantics: hoist to immediate parent even if it hoists); TsDeclareFunction always skip=1
// classes/enums/interfaces/type-aliases/modules:
//   hoisted_scope_id = scopes.get(scopes.len()-2)  — "the declaration owns its own scope,
//   so the NAME lives in the parent" (that's why `class A {}` makes A usable outside)
```

**Flow:** The scope table marks block-like scopes as hoist-through and every function/module/root as a barrier. Var walks up to the nearest barrier; function declarations skip their own (function-body) scope first; TS type-carrying declarations unconditionally target `len-2` because their node ALWAYS pushed its own scope. Strict mode changes ONLY the function case: inside strict code a nested function declaration hoists to the immediate enclosing scope rather than skipping further out.
**Invariant:** The `.filter(current != *id)` tail converts "target == here" into plain local registration — callers don't branch. Root scope asserts `DontHoistDeclarationsToParent` (debug_assert :1347-1350): hoisting can never escape the file. Class/enum DUAL bindings (Value+Type) both carry the same hoisted id — see ts-dual-slot-bindings.md.
**Probe:** `src/tests/references.rs::ok_hoisting_read_inside_function` (read-before-var inside f), `::ok_hoisting_read_var_inside_if` (var inside if hoists past block), `::ok_hoisting_inside_switch`, `::ok_class_reference`/`ok_class_expression_2` (rome issue 3779), `tests/scopes.rs::ok_scope_overloaded_functions`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "scope_index_to_hoist_declarations HoistDeclarationsToParent hoisted_scope_id DeclarationFound", limit: 10 });
```

## Verdict
Adopt the barrier-walk formulation (hoist-through flags on scope kinds + skip counts per declaration family); adapt the strict-mode annex-B nuance to your host's spec level; omit the separate hoisted-range index if you don't need the query.
