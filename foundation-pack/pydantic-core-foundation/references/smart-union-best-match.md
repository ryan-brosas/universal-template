<!-- capsule-v2 -->
# Smart union — how is the best-match choice selected and when does an early return happen?

**Source:** pydantic-core MIT `main@383eb95a19433754c0cecf7025b50c26b6d97a36`; Codebase Memory `ext-pydantic-core`. **Question:** What exact metric ranks union members in smart mode, and what makes a member win immediately?

## fields_set_count primary, exactness tiebreak; Exact+no-fields-set returns instantly; leftmost wins ties
**Path/Symbol:** `src/validators/union.rs:UnionValidator::validate_smart` (:103-183); `MaybeErrors` (:229-281).
**Signature:** `choices: Vec<(Arc<CombinedValidator>, Option<String>)>` (label from optional `(schema, "custom label")` tuple at build :64-71); `mode: UnionMode {Smart, LeftToRight}`.
**Data Shape:** `best_match: Option<(Py<PyAny>, Exactness, Option<usize>)>`; error accumulator `SmallVec<[ChoiceLineErrors; SMALL_UNION_THRESHOLD]>` with `SMALL_UNION_THRESHOLD = 4` (src/common/union.rs:43).

### Decisive source
```rust
let new_success_is_best_match: bool =
    best_match.as_ref().map_or(true, |(_, cur_exactness, cur_fields_set_count)| {
        match (*cur_fields_set_count, new_fields_set_count) {
            (Some(cur), Some(new)) if cur != new => cur < new,
            _ => *cur_exactness < new_exactness,
        }
    });
```

**Flow:** Per choice: reset trial metrics (`state.exactness = Some(Exactness::Exact); state.fields_set_count = None`) → validate → (a) success with `Exact` AND `fields_set_count == None` ⇒ restore old metrics and RETURN immediately (:121-130); (b) other success ⇒ compare per the ladder above, keep best; (c) `LineErrors` ⇒ push into accumulator ONLY while no best match exists yet (:161-163) — once a best exists, later failures are not even recorded (error-volume optimization); (d) non-LineErrors errors (InternalErr/Omit/UseDefault) propagate untouched (`otherwise => return otherwise`, :165). After the loop: restore ambient metrics, then winner applies `state.floor_exactness(exactness)` + `add_fields_set(count)` onto the restored state (:173-178). No match ⇒ `errors.into_val_error(input)` — each line gets `err.with_outer_location(case_label)` where label = custom label or `choice.get_name()` (that's why validator names must contain NO spaces/dots, see tagged-union descr comment :321-323). Custom error replaces the whole body when configured (`MaybeErrors::Custom` discards pushes entirely).
**Invariant:** Trial metrics are reset before EVERY choice; the winner's quality is merged back via floor+add so sibling validators see honest numbers. Leftmost-wins on full ties (map_or(true) keeps the earlier best). `mode='left_to_right'` skips all of this — first success wins, no ranking (:185-201).
**Probe:** `grep -c 'fn validate_smart' src/validators/union.rs` =1; `grep -n 'SMALL_UNION_THRESHOLD' src/common/union.rs` → `43:pub(crate) const SMALL_UNION_THRESHOLD: usize = 4;`; direct tests: tests/validators/test_union.py::TestSmartUnionWithDefaults::test_fields_set_ensures_best_match :885-891 ("defaults to leftmost choice if there's a tie" asserted via `{}` input), test_smart_union_default_fallback :598 — suite green this pass (83 passed, 1 xfailed).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-pydantic-core", query: "validate_smart best match fields_set exactness", limit: 5 });
// live rank-1: TestSmartUnionWithDefaults.test_fields_set_ensures_best_match tests/validators/test_union.py :885-891;
// rank-2 the source itself :103-183
```

## Verdict
Adopt: two-metric ranking with instant-exact short-circuit, stop-recording-errors-after-first-success, outer-location-per-choice error envelope. Adapt metric set if your models lack fields_set tracking (then exactness-only). Omit nothing: dropping the "errors only until first success" rule produces quadratic error lists on wide unions.
