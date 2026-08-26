<!-- capsule-v2 -->
# Closure capture traversal — captures computed from scope graphs, with a dead-field trap

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** How do you enumerate what a closure captures (excluding nested closures' own captures) using only a prebuilt scope/reference model?

## AllCapturesIter: worklist over child scopes + parent-containment filter
**Path/Symbol:** `crates/biome_js_semantic/src/semantic_model/closure.rs` — `Closure::from_node/from_scope` (:231-246), `all_captures` (:284-316), `AllCapturesIter::next` (:126-163), `ChildrenIter` vs `DescendentsIter` (:169-221), `CaptureType::{ByReference,Type}` (:74-78); closure-node set via `SyntaxTextRangeHasClosureAstNode!` macro (:15-72) generating `AnyHasClosureNode` over exactly 10 callable kinds.
**Signature:** `closure.all_captures() -> impl Iterator<Item = Capture>`; Capture exposes `.node()` (the reference site), `.binding()` (target), `.declaration_range()` (fast path reading the stored binding range instead of re-resolving the node).
**Data Shape:** Iteration state = `closure_range` + stack of `ScopeId`s + stack of `ReferenceId`s; a capture qualifies when `!closure_range.contains(binding.range.start())` — i.e., the REFERENCED BINDING is declared outside the closure.

### Decisive source
```rust
'scopes: while let Some(scope_id) = self.scopes.pop() {
    let scope = &self.data.scopes[scope_id.index()];
    if scope.is_closure { continue 'scopes; }        // NEVER descend into nested closures
    self.references.clear();
    self.references.extend(scope.read_references.iter().copied());
    self.references.extend(scope.write_references.iter().copied()); // see invariant: write_references is DEAD
    self.scopes.extend(scope.children.iter());
}
// seed: own scope refs + PARENT-scope refs filtered to those physically inside this closure
if let Some(parent) = scope.parent {
    let within: Vec<_> = parent_scope.read_references.iter()
        .filter(|r| self.is_reference_within_scope(scope, r)).collect(); // any ref of the binding lands in scope.range
```

**Flow:** Seed with the closure scope's references, plus the parent scope's references filtered to those whose reference RANGES fall inside the closure text (this catches shorthand/global-ish usages recorded at the parent level), then BFS child scopes skipping `is_closure` ones. Each surviving ReferenceId yields a Capture iff its binding was declared outside the closure span. `children()` walks until the FIRST closure descendant (immediate closures only); `descendents()` includes self and keeps descending past closures.
**Invariant:** THE TRAP: `SemanticModelBuilder.push_event` never appends to `scope.write_references` (verified by grep — only `read_references.push` exists; grep of the whole crate shows zero writers), yet closure.rs still extends from it. Porters who "fix" the asymmetry by reading ONLY read_references lose write-captures (`a = 1` inside f capturing outer `a` — pinned by `ok_closure writes` case :490-494); porters who copy the field blindly carry dead weight. Also: `Capture.ty()` is ALWAYS ByReference today — `CaptureType::Type` has no producer.
**Probe:** `closure.rs` embedded `#[cfg(test)] mod test` (:375-520) — `ok_semantic_model_closure` covers two-capture, inner-function (`f` captures `[a]`, `g` captures `[b,c]`), arrow, write-capture, and class/object member callables (constructor/getter/setter/method all count as closures).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "AllCapturesIter all_captures CaptureType is_closure children descendents", limit: 10 });
```

## Verdict
Adopt the worklist + containment-filter algorithm; ADAPT AWAY the phantom `write_references` reads (either populate both or merge into one list) — copying it verbatim imports a latent bug; omit CaptureType until you need by-value captures.
