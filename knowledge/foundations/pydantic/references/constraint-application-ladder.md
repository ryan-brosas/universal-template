<!-- capsule-v2 -->
# Constraint application ladder — what happens when a known constraint does not fit the schema type directly?

**Source:** pydantic MIT `main@2151025a`; Codebase Memory `pydantic`. **Question:** Given a collected constraint like `pattern='abc'` and a schema that is not a plain string, how does pydantic decide between setting a key, wrapping in a validator, chaining, or failing — and where do the failures surface?

## Connected graph-selected seam
**Path/Symbol:** `pydantic/_internal/_known_annotated_metadata.py:apply_known_metadata` (:171-341); support table `CONSTRAINTS_TO_ALLOWED_SCHEMAS` :55-106; error contract `check_metadata` :389-405; fallback table `_validators.NUMERIC_VALIDATOR_LOOKUP` :482-492.
**Signature:** `apply_known_metadata(annotation: Any, schema: CoreSchema) -> CoreSchema | None`.
**Data Shape:** one already-expanded annotation + one core schema; returns the updated schema, or `None` meaning "this annotation is not a known constraint — leave the schema alone". The allowed-set table is built by inverting `constraint_schema_pairings` (constraint set × schema-type tuple) into `defaultdict(set)` at import time.

### Decisive source
```python
schema = schema.copy()  # never mutate the caller's schema
schema_update, other_metadata = collect_known_metadata([annotation])
schema_type = schema['type']
...
if schema_type in {'function-before', 'function-wrap', 'function-after'} and constraint == 'strict':
    schema['schema'] = apply_known_metadata(annotation, schema['schema'])
    return schema
# if we're allowed to apply constraint directly to the schema, like le to int, do that
if schema_type in allowed_schemas:
    if constraint == 'union_mode' and schema_type == 'union':
        schema['mode'] = value
    else:
        schema[constraint] = value
    continue
# else, apply a function after validator ...
if constraint in chain_schema_constraints:          # pattern/strip_whitespace/to_lower/to_upper/coerce_numbers_to_str/ascii_only
    ... cs.no_info_wrap_validator_function(_apply_constraint_with_incompatibility_info, cs.str_schema(**{constraint: value}))
elif constraint in NUMERIC_VALIDATOR_LOOKUP:         # gt/ge/lt/le/multiple_of/min_length/max_length/max_digits/decimal_places
    schema = cs.no_info_after_validator_function(partial(NUMERIC_VALIDATOR_LOOKUP[constraint], **{constraint: value}), schema)
    metadata['pydantic_js_updates'] = {js_constraint_key: as_jsonable_value(value)}   # min_length→minItems for list/json-or-python-list
elif constraint == 'allow_inf_nan' and value is False:
    schema = cs.no_info_after_validator_function(forbid_inf_nan_check, schema)
else:
    raise RuntimeError(f"Unable to apply constraint '{constraint}' to schema of type '{schema_type}'")
...
# remainder: at.Predicate / at.Not → after-validator raising PydanticCustomError('predicate_failed'/'not_operation_failed')
# anything else unknown → return None
```

**Flow:** copy schema → partition the single annotation → per known constraint walk the ladder: strict-on-function recurses inward; direct key-set when the schema type is in the constraint's allowed set (`union_mode` writes `mode`, not `union_mode`); str-chain constraints become wrap-validators around a fresh `str_schema` whose downstream type-errors are re-raised as `TypeError "Unable to apply constraint ..."`; numeric/length constraints become after-validators with a JSON-schema update stamp; `allow_inf_nan=False` becomes the finite-number check; unhandled → RuntimeError → then handle the remainder (Predicate/Not become coded custom errors; any other unknown ⇒ return None) → compose accumulated str-chain steps with `cs.chain_schema([schema] + steps)`.
**Invariant:** the caller's schema object is never mutated (copy-first); returning None is a first-class result meaning "unknown annotation", and the CALLER must then return the original schema unchanged — unknown metadata is silently ignored, not an error; incompatible str-chain constraints fail at FIRST USE (validation time) as TypeError, not at build time; JSON updates are merged into existing `pydantic_js_updates`, never replaced.
**Probe:** `tests/test_annotated.py::test_incompatible_metadata_error` :613-616 (`Annotated[list[int], Field(pattern='abc')]` raises `TypeError: Unable to apply constraint 'pattern'` on first validate) and `::test_compatible_metadata_raises_correct_validation_error` :619-623 (same constraint through a before-validator chain yields the normal string-pattern ValidationError); `::test_predicate_error_python` :393-407 pins the coded `'predicate_failed'` message including the lambda qualname.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pydantic", query: "apply_known_metadata CONSTRAINTS_TO_ALLOWED_SCHEMAS NUMERIC_VALIDATOR_LOOKUP", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-rung ladder (direct key-set → wrap-chain → after-validator+js-stamp → RuntimeError) and the None-means-unknown contract; adapt the allowed-set table to your host's schema kinds; omit the js_updates stamping if your host has no JSON layer. Caveat: `check_metadata` has zero in-tree callers at this pin — it is the intended error contract for internal implementations, not live behavior. Retrieve written but not executed this pass (MCP unavailable).
