<!-- capsule-v2 -->
# TestModel schema data generator fixes — which truthiness habits corrupt test-data generation?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** What do falsy-value bugs in a JSON-Schema-driven generator look like, and what are the correct forms?

## testmodel-generator-falsy-fixes
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/test.py:` `_JsonSchemaTestData._gen_any` const branch (:463–464), `_int_gen` equal-bounds branch (:537–539); stream-cancel simulation `_StreamCancelled` (:347,:383) + `get_stream_cancel_errors` override (:434–435).
**Signature:** `if 'const' in schema: return schema['const']` / `minimum = schema.get('minimum'); if minimum is not None and maximum == minimum: return minimum`.
**Data Shape:** schema dicts with JSON-Schema keywords; generated values must satisfy the schema exactly (TestModel feeds them as validated tool args / outputs).

### Decisive source
```python
# BEFORE (two real bugs):            # AFTER:
if const := schema.get('const'):    | if 'const' in schema:
    return const                    |     return schema['const']      # falsy consts (0, '', False, None) survive
                                    |
maximum = schema.get('maximum')     | minimum = schema.get('minimum')
...                                 | if minimum is not None and maximum == minimum:
minimum = schema.get('minimum')     |     return minimum              # min==max inclusive bounds now satisfiable
```

**Flow:** `_gen_any` hits `const: 0` → old walrus dropped it into enum/examples handling → generated invalid data; new membership check returns the falsy const verbatim. `_int_gen`: schemas like `{minimum: 5, maximum: 5}` previously fell through generic generation producing out-of-range values; the equality pre-check short-circuits. Separately, TestStreamedResponse raises its OWN `_StreamCancelled` exception mid-stream and declares it via `get_stream_cancel_errors()` — the test double no longer depends on httpx internals (commit fde1bbb replaced truthiness guards with explicit `is not None` checks in streamed deltas too).
**Invariant:** three rules:
1. In schema-driven generation, EVERY value lookup must be membership-or-is-not-None — walrus/`get()` truthiness silently discards legal JSON values (0, "", false, null).
2. Inclusive-bound equality needs an explicit early return; range logic assuming max>min generates invalid fixtures.
3. Test doubles simulating transport cancellation should define a private exception and register it through the SAME seam production code queries (`get_stream_cancel_errors`) — coupling the fake to httpx.StreamClosed made the fake wrong the moment transports migrated.
**Probe:** `tests/models/test_model_test.py::test_json_schema_test_data_falsy_const` (parametrized :602), `::test_json_schema_test_data_equal_inclusive_bounds` (:561), `::test_falsy_const_tool_args` (:612).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_JsonSchemaTestData _gen_any const _int_gen minimum maximum TestStreamedResponse", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the membership-test discipline for any schema walker generating or filtering values; adapt keywords; the `_StreamCancelled` seam-registration trick is adopt-anywhere for transport-agnostic fakes.
