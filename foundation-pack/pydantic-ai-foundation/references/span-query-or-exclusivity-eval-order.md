<!-- capsule-v2 -->
# Query-DSL evaluation order — what order must a dict-shaped recursive query DSL evaluate its conditions in, and why must OR be exclusive at a level?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter designing a serializable recursive query DSL (dict of optional conditions) must fix an evaluation order that is cheap, unambiguous under boolean mixing, and reviewable against the schema — and decide what happens when a user writes `{'name_equals': X, 'or_': [...]}`.

## Combinators first, cheapest conditions first, OR exclusive at a level
**Path/Symbol:** `pydantic_evals/pydantic_evals/otel/span_tree.py:SpanNode._matches_query` (:276-407), `SpanQuery` field-order docstring (:34-37), per-query `@cache` locals `descendants/pruned_descendants/ancestors/pruned_ancestors` (:345-355/:377-385).
**Signature:** `_matches_query(self, query: SpanQuery) -> bool` — recursive; sub-queries are plain dicts evaluated by the same method.
**Data Shape:** one dict per level; keys are either combinators (`or_`, `not_`, `and_`) or leaf conditions; recursion depth = nesting of dicts.

### Decisive source
```python
def _matches_query(self, query: SpanQuery) -> bool:  # noqa: C901
    # Logical combinations
    if or_ := query.get('or_'):
        if len(query) > 1:
            raise ValueError("Cannot combine 'or_' conditions with other conditions at the same level")
        return any(self._matches_query(q) for q in or_)
    if not_ := query.get('not_'):
        if self._matches_query(not_):
            return False
    if and_ := query.get('and_'):
        results = [self._matches_query(q) for q in and_]
        if not all(results):
            return False
    # At this point, all existing ANDs and no existing ORs have passed, so it comes down to this condition

    # Name conditions
    if (name_equals := query.get('name_equals')) and self.name != name_equals:
        return False
    ...
```

**Flow:** within one level: `or_` FIRST — it may not coexist with any other key (`len(query) > 1` → ValueError) and returns immediately, so it cannot be AND-ed; then `not_` (early False); then `and_` (all-must-pass); then individual conditions in documented cheapest-first order (name → attributes → status → timing → children → descendants → ancestors). The `SpanQuery` TypedDict's field order is deliberately kept identical to this evaluation order, with a docstring saying so "for easy review" — schema and implementation stay walkable side by side. Related-span conditions use PER-CALL local `@cache`d closures because min/max count guards AND some/all/no quantifiers can each re-walk the same subtree inside ONE matches() call; the cache lives on the local function, so no state leaks across queries.
**Invariant:** two rules: (1) `or_` is EXCLUSIVE at its level because `{'name_equals': X, 'or_': [A, B]}` is ambiguous between `(X AND (A OR B))` and `(X OR A OR B)` — the DSL refuses the ambiguity instead of guessing a precedence; (2) condition order is part of the contract — cheap checks first, and the TypedDict documents the same order, so a reviewer can verify both in one pass.
**Probe:** `tests/evals/test_otel.py::test_or_cannot_be_mixed` (:952-956) pins the exact ValueError message via snapshot; `test_span_query_logical_combinations` (:672-710) pins AND/OR/complex-composition match counts on a 4-span tree; `test_span_query_negation` (:640-670) pins not_ composition. Suite EXECUTED GREEN at pin this pass (29 passed).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_matches_query or_ and_ not_ Cannot combine", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of span_tree.py :276-407/:34-37 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt combinator-first evaluation with an EXCLUSIVE top-level OR (raise on mixing rather than inventing precedence) for any dict-shaped recursive query DSL — silent precedence guesses are how DSLs accumulate ambiguity. Adopt the schema-order-documents-evaluation-order discipline and per-call cached derived collections when multiple guards share an expensive walk. Adapt the condition vocabulary; omit the @cache locals if your related-span conditions cannot be combined with count guards. Coverage caveat: none — span_tree.py read whole this pass.
