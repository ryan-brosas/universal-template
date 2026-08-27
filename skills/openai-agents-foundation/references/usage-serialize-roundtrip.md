<!-- capsule-v2 -->
# Usage serialize/deserialize round trip — what wire shape does a token ledger persist, and how does deserialization tolerate legacy snapshots?

**Source:** OpenAI Agents Python MIT `main@fe45b415`; Codebase Memory `openai-agents-python`. **Question:** When a usage ledger must survive serialization across SDK versions (new detail fields appear, old snapshots lack them), what exact wire shape do you write, and how do you read back both the new and the legacy shapes without failing the run?

## Legacy list shape at top level + dict entries + field-defaulting coercion
**Path/Symbol:** `src/agents/usage.py:` `_coerce_input_token_details` (:95–109), `deserialize_usage` (:111–149), `_serialize_usage_details` (:386–393), `_serialize_input_tokens_details` (:395–403), `serialize_usage` (:405–432).
**Signature:** `serialize_usage(usage: Usage) -> dict[str, Any]`; `deserialize_usage(usage_data: Mapping[str, Any]) -> Usage`.
**Data Shape:** serialized top-level `input_tokens_details` / `output_tokens_details` are SINGLE-ELEMENT LISTS (legacy wire shape kept for compatibility) while each `request_usage_entries[i]` detail is a plain DICT; input details always carry both `cached_tokens` and `cache_write_tokens` (cache-write back-filled from the live details object when the installed pydantic model version lacks the field); output details default to `{"reasoning_tokens": 0}`.

### Decisive source
```python
# serialize_usage: top level stays a 1-element list, entries are dicts
return {
    "requests": usage.requests,
    "input_tokens": usage.input_tokens,
    "input_tokens_details": [input_details],
    "output_tokens": usage.output_tokens,
    "output_tokens_details": [output_details],
    ...
}

# _coerce_input_token_details: accept list OR mapping, default the new field
candidate = raw_value
if isinstance(candidate, list) and candidate:
    candidate = candidate[0]
if isinstance(candidate, Mapping):
    candidate = {**candidate, "cache_write_tokens": candidate.get("cache_write_tokens", 0) or 0}
try:
    return TypeAdapter(InputTokensDetails).validate_python(candidate)
except ValidationError:
    return _make_input_tokens_details()
```

**Flow:** serialize: each details object is `model_dump()`-ed when non-empty, else the default dict is used; input details then get `cached_tokens` and `cache_write_tokens` force-present (None→0; cache-write read via getattr-style fallback so older openai package versions without the field still serialize 0) → deserialize: top-level and per-entry input details pass through `_coerce_input_token_details` which unwraps a single-element list, injects `cache_write_tokens=0` for pre-cache-write snapshots, validates with TypeAdapter, and falls back to fresh zero-details on ValidationError (a corrupt snapshot degrades to zeros rather than raising); output details use the same coerce helper with `{"reasoning_tokens": 0}` as both the missing-value fill and the validation fallback; scalar fields default to 0 via `.get(key, 0)`; per-request entries are rebuilt one-by-one through the same coercers.
**Invariant:** round-trip stability — `deserialize_usage(serialize_usage(u))` preserves cache-read AND cache-write counts at both the top level and every request entry; any snapshot written before a detail field existed deserializes with that field defaulted to 0 instead of failing; the top-level list shape is preserved on write so old readers keep working.
**Probe:** `tests/test_usage.py::test_usage_serialization_preserves_cache_write_tokens` (:569 — `serialized["input_tokens_details"] == [{"cached_tokens": 3, "cache_write_tokens": 7}]` and restored values equal at both levels), `::test_usage_deserialization_defaults_legacy_cache_write_tokens` (:606 — snapshot lacking `cache_write_tokens` restores it as 0 at both levels), `::test_usage_snapshot_delta_and_span_preserve_cache_write_tokens` (:638 — delta of two snapshots keeps cache-write arithmetic intact).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openai-agents-python", file_pattern: "usage.py", query: "serialize_usage deserialize_usage cache_write_tokens", limit: 20 });
await mcp.codebase_memory.get_code_snippet({ project: "openai-agents-python", qualified_name: "openai-agents-python.src.agents.usage._coerce_input_token_details" });
```

## Verdict
Adopt the write-legacy-shape/read-both-shapes pattern for any ledger that outlives its writer version: keep the on-disk shape stable (even when the in-memory model changes), default new fields at read time, and degrade corrupt snapshots to safe defaults instead of raising mid-run. Adapt the default dicts and the list-vs-dict legacy quirk to your own wire format. Omit the per-request entry plane if you never need per-call accounting. Coverage: direct source+test reading fallback this pass (Codebase Memory MCP not connected); cited ranges read from checkout at fe45b415.
