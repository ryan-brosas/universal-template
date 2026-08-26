<!-- capsule-v2 -->
# Constraint extraction & fuel — how do you turn a filter tree into per-target constraint sets without exploding?

**Source:** meilisearch MIT `main@577f7af2`; Codebase Memory `ext-meilisearch`. **Question:** How does DNF-style constraint extraction handle NOT polarity, OR/AND duality, and combinatorial blowup with a saturating fuel meter?

## FilterConstraints.evaluate_filter / evaluate_and
**Path/Symbol:** `crates/filter-parser/src/constraint.rs` (`FilterConstraintSet` :9, `ConstraintTarget` :17-21, `evaluate_filter` :38-148, `evaluate_and` :150-186, `max_number_of_constraints` :188-190, `FilterConstraintFuel` :203-254).
**Signature:** `pub fn new(filter: &IndexFilterCondition, fuel: &mut FilterConstraintFuel) -> Self`; `fn evaluate_and(conds: &Vec<IndexFilterCondition>, polarity: bool, fuel) -> FilterConstraintSet`.
**Data Shape:** Output = `Vec<BTreeMap<ConstraintTarget, Vec<ConstraintCondition>>>` — one MAP per disjunctive branch; targets are Fid/Vector{fid,embedder}/Geo so constraints group by attribute; fuel = `(or: u16, and: u16, depth: u8)` with Saturating arithmetic.

### Decisive source
```rust
// constraint.rs:72-99 — De Morgan duality: under negation AND/OR swap ROLES
IndexFilterCondition::Or(index_filter_conditions) => {
    if polarity {
        // OR means a new list of constraints
        for cond in index_filter_conditions {
            if fuel.consume_or_fuel().is_break() { break; }
            Self::evaluate_filter(constraints, cond, true, fuel);
        }
    } else {
        let mut conjunction = Self::evaluate_and(index_filter_conditions, false, fuel);
        constraints.append(&mut conjunction);
    }
}
```
```rust
// constraint.rs:164-167 — the cartesian-product fuse, capped by fuel
conjunction = conjunction.drain(..)
    .cartesian_product(std::mem::take(&mut local_constraints))
    .take_while(|_| fuel.consume_and_fuel().is_continue())
    .map(|(left, right)| /* merge_join_by target: append condition lists */ ...)
    .collect();
```

**Flow:** Walk the tree carrying a polarity flag: `Not` flips polarity (no tree rewrite); positive Condition/VectorExists/Geo* push a fresh single-entry map onto the set; positive OR appends each branch as its own map (new disjunct); positive AND fuses via cartesian product merging same-target condition lists; NEGATED branches invert the roles (OR-under-not becomes an AND-fuse, AND-under-not becomes branch-per-element). IN-desugar is explicit: `In` ⇒ Or of Equals. Depth fuel restores on exit (`restore_depth_fuel`) while or/and fuel only drains — once any fuel hits 0 the walk truncates silently and `is_exhausted()` reports it.
**Invariant:** (1) Each output map is one CONJUNCTIVE scenario — callers must satisfy ALL maps' targets being satisfiable-or-empty per their semantics (used for settings-time validation of what filters COULD touch which fields); (2) fuel exhaustion yields a PARTIAL result, never an error — consumers must check `is_exhausted()` before trusting coverage claims; (3) merge_join_by keeps BTreeMap ordering so identical targets from both sides concatenate.
**Probe:** exercised via `crates/milli/src/search/facet/filter/tests.rs` + index-scheduler dsr tests naming `dsr_fuel`; direct observable this pass: `cargo test -p filter-parser --lib` GREEN at pin (constraint module compiles into the crate's 11 passing tests). Coverage caveat: no dedicated unit test enumerates constraint sets — pinned transitively.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-meilisearch", query: "FilterConstraints evaluate_filter polarity fuel cartesian_product", limit: 10 });
```

## Verdict
Adopt the polarity-carrying walk, role-swap-under-negation, target-keyed fusion, and the three-meter fuel model; adapt BTreeMap grouping to host; omit the DSR (document-support-rules) consumer context.
