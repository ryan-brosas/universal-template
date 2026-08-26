<!-- capsule-v2 -->
# Filter expression algebra — how do you give vector stores one filter model that works for human code AND LLM JSON output without a backend online?

**Source:** graphrag MIT `main@6dad6d2b059589624035714d8dcfde94ecc0a5fb`; Codebase Memory `graphrag`. **Question:** what does the pydantic filter-expression contract look like so the same tree can be built fluently in Python, round-tripped as LLM-generated JSON, evaluated client-side, or compiled per backend?

## FilterExpr union + client-side evaluate
**Path/Symbol:** `packages/graphrag-vectors/graphrag_vectors/filtering.py` (`Condition.evaluate` :81-103, `_compare` :115-146, `AndExpr` :161-192, `OrExpr` :195-226, `NotExpr` :229-257, `FilterExpr` union :261-264).
**Signature:** `Condition(field: str, operator: Operator, value: Any).evaluate(obj) -> bool`; `Operator` StrEnum = eq/ne/gt/gte/lt/lte/contains/startswith/endswith/in_/not_in/exists (:42-56).
**Data Shape:** `FilterExpr = Annotated[Condition | AndExpr | OrExpr | NotExpr, Field(discriminator=None)]` — a deliberately NON-discriminated union; containers carry `and_ list[FilterExpr]`, `or_`, `not_` with `populate_by_name=True`.

### Decisive source
```python
# filtering.py:96-103 — exists is the ONLY operator allowed a missing field;
# every other operator returns False for None (never raises)
if self.operator == Operator.exists:
    exists = actual is not None
    return exists if self.value else not exists
if actual is None:
    return False
return self._compare(actual, self.operator, self.value)
```
```python
# filtering.py:176-178 — field resolution ladder: dict → attr → obj.data dict → None
if isinstance(obj, dict):
    return obj.get(self.field)
if hasattr(obj, self.field):
    return getattr(obj, self.field)
if hasattr(obj, "data") and isinstance(obj.data, dict):
    return obj.data.get(self.field)
```

**Flow:** build (`F.field op value` or LLM JSON `{model_validate}`) → combine with `&`/`|`/`~` overloads (each returns a NEW node; `_make_and/_make_or` FLATTEN same-kind children so `(a&b)&c` is one AndExpr of 3) → either `.evaluate(obj)` client-side against dicts/dataclasses/`.data` dicts, or backend `_compile_filter(expr)`.
**Invariant:** missing-field semantics are fail-closed-False EXCEPT `exists`, which is truthy-parameterized (`F.f.exists(False)` means "field must be absent"); `in_`/`not_in` return False when value is not a list instead of raising; type-mismatched contains/startswith/endswith on non-strings are False, not errors.
**Probe:** `tests/unit/vector_stores/test_filtering.py` — `test_missing_field_returns_false` (:60), `test_and_flattening` asserts `len(expr.and_) == 3` (:214-218), `test_double_negation` asserts `~(~inner)` IS the Condition (:233-240), `test_complex_nested_roundtrip` re-evaluates after JSON round-trip (:305-323). Suite runs offline: `/home/utopia/.venvs/grag-lane-venv/bin/python -m pytest tests/unit/vector_stores/test_filtering.py -q` → 34 passed @pin.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "graphrag", query: "FilterExpr Condition evaluate filter expression", limit: 10, fields: ["signature", "name", "file"] });
```
Live-resolved rank#1 `filtering.Condition.evaluate` :81-103.

## Verdict
Adopt the four-node algebra, flattening combinators, double-negation identity, and fail-closed missing-field rule; adapt operator set and serialization alias style to host; omit CosmosDB/LanceDB-specific compilers (see lancedb-filter-compiler capsule). Direct tests run backend-free — no coverage caveat.
