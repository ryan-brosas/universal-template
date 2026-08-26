<!-- capsule-v2 -->
# Rule registry dispatch — how do you get O(1) per-node rule dispatch with zero virtual dispatch in the hot loop?

**Source:** Biome MIT `main@6cd32636f463551b8dfe46aeefb1191d437b4694`; Codebase Memory `biome`. **Question:** hundreds of rules over millions of nodes need dispatch cheaper than a trait-object walk — how does the registry map a query match to its rules and what does a porter break by misregistering?

## The registry seam
**Path/Symbol:** `crates/biome_analyze/src/registry.rs` — `RuleRegistry` (:99-102), `PhaseRules` (:123-129), `TypeRules` (:131-134), `RuleRegistryBuilder::record_rule` (:162-225), `match_query` (:256-290), `RegistryRule::new` (:381-465), `Phases`/`Phase` (:19-37).
**Signature:** `type RuleExecutor<L> = fn(&mut MatchQueryParams<L>, &mut RuleState<L>) -> Result<(), Error>` — a plain fn POINTER, not a boxed closure; `RegistryRule { run: RuleExecutor<L>, state_index: usize }`.
**Data Shape:** `phase_rules: [PhaseRules<L>; 2]`; `type_rules: FxHashMap<TypeId, TypeRules>` where `TypeRules::SyntaxRules { rules: Vec<SyntaxKindRules> }` is a sparse vector indexed by `usize::from(RawSyntaxKind)` vs `TypeRules::TypeRules { rules: Vec<RegistryRule> }` for arbitrary TypeId queries; `rule_states: Vec<RuleState>` holds per-rule suppression sets, referenced by index.

### Decisive source
```rust
// registry.rs:188-204 — kind-indexed dense-ish vector: resize to max kind seen,
// push rule handle into every kind slot the node's KIND_SET covers:
for kind in key.iter() {
    let RawSyntaxKind(index) = kind.to_raw();
    let index = usize::from(index);
    if rules.len() <= index {
        rules.resize_with(index + 1, SyntaxKindRules::new);
    }
    let node = &mut rules[index];
    node.rules.push(rule);
}
```
```rust
// registry.rs:394-398 — node-level suppression short-circuit INSIDE the executor:
if let Some(node) = params.query.downcast_ref::<SyntaxNode<RuleLanguage<R>>>()
    && state.suppressions.inner.contains(node)
{ return Ok(()); }
```
**Flow:** builder walks categories→groups→rules (each level filter-gated by `AnalysisFilter`, :149-168); each accepted rule lands in its phase's map keyed either by `TypeId::of::<SyntaxNode<L>>()` (SyntaxKey) or the query's own TypeId; registering ALSO calls `<R::Query as Queryable>::build_visitor(...)` so visitors are collected during registration (:223). At match time: `type_rules.get(&query.type_id())` → for SyntaxRules downcast to `SyntaxNode<L>` and index by raw kind → run every executor with its `rule_states[state_index]`. Errors from executors are SWALLOWED with only a TODO comment (`let _ = (rule.run)(...)` #3394, :286-287) — a panicking rule aborts via catch_unwind upstream, but Err here is silent. Misregistration is a loud `unreachable!`: registering a `QueryKey::TypeId(SyntaxNode)` or a Syntax key colliding with an existing TypeId entry panics with a message naming the cause (:182-184, :212-214).
**Invariant:** dispatch cost is hashmap-lookup + vec-index + fn-pointer call — no dyn Visitor in the rule path; state lives OUTSIDE the rule handle so `RegistryRule` stays `Copy`; phases are indexed arrays, never looked up by name. A porter who keys by SyntaxNode TypeId AND expects TypeId queries on the same type gets the documented panic.
**Probe:** `crates/biome_analyze/src/matcher.rs` tests exercise the full registry through `Analyzer::new(&metadata, &mut matcher, ...)` with real rules asserting emitted order/ranges (47 < 63 < 76 < 97 < 110 strictly increasing, :201-380); registry.rs:180-184 unreachable! text is itself the contract test target.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "biome", query: "RegistryRule RuleExecutor match_query record_rule", limit: 10, fields: ["signature", "name", "file"] });
// RegistryRule.state_index registry.rs 356; RuleExecutor 379; RegistryRule.new 382-465 (line-exact)
```

## Verdict
Adopt TypeId→(kind-vector | type-rules) two-tier dispatch with monomorphized fn-pointer executors and out-of-band state indexing; adapt the phase count and filter model; omit the unreachable! twin-registration ladders only if your host cannot have the collision. Coverage caveat: no single integration test isolates registration collisions — the unreachable! branches are the pin.
