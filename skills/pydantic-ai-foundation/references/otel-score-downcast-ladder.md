<!-- capsule-v2 -->
# OTel score downcast ladder — how do heterogeneous evaluator outputs (bool/int/float/str) become queryable score attributes?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter whose evaluators return booleans, numbers, AND categorical strings must map every scalar onto a fixed pair of queryable attributes without losing information, and render a short human-readable body for the live trace view.

## Dual-representation bools; one-of for the rest
**Path/Symbol:** `pydantic_evals/pydantic_evals/_otel_emit.py:_set_score_attrs` (:218-232); `_format_score` (:201-215); `_format_result_body` (:185-191).
**Signature:** `_set_score_attrs(attrs: dict[str, Any], value: Any) -> None` (mutates in place); `_format_score(value: Any) -> str`.
**Data Shape:** Two target attributes: `gen_ai.evaluation.score.value` (numeric) and `gen_ai.evaluation.score.label` (categorical). The mapping is type-driven and exhaustive over the scalar contract.

### Decisive source
```python
def _set_score_attrs(attrs, value):
    # - bool → both: score.value = 0.0/1.0, score.label = "pass"/"fail".
    #   Dual representation so numeric queries and categorical queries both work.
    # - int/float → score.value only.
    # - str → score.label only (evaluator returned a categorical tag).
    if isinstance(value, bool):
        attrs[_ATTR_SCORE_VALUE] = 1.0 if value else 0.0
        attrs[_ATTR_SCORE_LABEL] = 'pass' if value else 'fail'
    elif isinstance(value, (int, float)):
        attrs[_ATTR_SCORE_VALUE] = float(value)
    elif isinstance(value, str):
        attrs[_ATTR_SCORE_LABEL] = value

def _format_score(value):
    if isinstance(value, bool):
        return 'True' if value else 'False'     # literal, not 1/0
    if isinstance(value, float):
        return format(value, 'g')               # drops trailing zeros; sci-notation ok
    if isinstance(value, str):
        return repr(value)                      # quoted so it reads like a value
    return str(value)
```

**Flow:** Each result's scalar is downcast by type: bools get BOTH attributes (1.0/0.0 plus 'pass'/'fail') so the same event answers "what fraction passed?" (numeric aggregate) and "group by pass/fail" (categorical group-by); ints/floats get `score.value` as a float only; strings get `score.label` only; anything outside the scalar contract (defensive `None`) sets NEITHER attribute rather than guessing. The log body renders the same value with display rules: bools as literal `True`/`False`, floats via `'g'` format, strings quoted via `repr`, ints bare — e.g. `evaluation: Tone='neutral'`.
**Invariant:** The `isinstance(value, bool)` branch MUST precede the `(int, float)` branch because `bool` subclasses `int` in Python — reversed order would emit `score.value=1.0` with no label for every boolean and destroy the categorical axis. For non-bool scalars exactly ONE of the two attributes is set; dual-setting is reserved for bools alone.
**Probe:** `tests/evals/test_otel_emit.py::test_bool_false_emits_fail_label` (:83-92) pins 0.0 + 'fail'; `test_numeric_score_only` (:95-104) pins value-only with label absent; `test_string_label_only` (:107-116) pins label-only with value absent; `test_non_scalar_value_yields_no_score_attrs` (:232-243) pins the defensive fall-through on `None`; `test_body_formatting_for_score_types` (:246-267) pins all five body renderings byte-for-byte including `"evaluation: Tone='neutral'"`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_set_score_attrs _format_score score.value score.label pass fail", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of _otel_emit.py :185-232 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the dual-representation bool rule — it is the single decision that lets one event serve both numeric aggregation and categorical grouping, and it is cheap to copy. Adopt the ordered type ladder with the bool-first guard and the no-guessing fall-through (unknown types emit no score attrs rather than a coerced one). Adapt the pass/fail label vocabulary to your domain if needed, but keep value+label paired for booleans. Omit the `'g'` float formatting detail unless you render inline bodies. Coverage caveat: none — _otel_emit.py read whole this pass.
