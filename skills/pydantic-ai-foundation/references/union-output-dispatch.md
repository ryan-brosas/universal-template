<!-- capsule-v2 -->
# UnionOutputProcessor kind-trust ladder — dispatching union outputs when hooks swap types

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** How does a discriminated union of output types stay correct when a hook replaces the validated value with a different member's type?

## UnionOutputProcessor.hook_execute
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_output.py:UnionOutputProcessor` (:1066-1314; `hook_execute` :1223-1254, `_semantic_matches_inner` :1256-1273, `_resolve_inner_for_value` :1275-1294, envelope construction :1101-1160).
**Signature:** `UnionOutputProcessor(outputs, *, name=None, description=None, strict=None)`; wire schema `{'result': {'kind': <const member-name>, 'data': <member-schema>}}` under an `anyOf`.
**Data Shape:** `_processors: dict[str, ObjectOutputProcessor]` keyed by member name (deduped `_2`, `_3`…); validation returns internal `_UnionValidatedOutput(kind, data)` where `data` is ALREADY the unwrapped semantic value.

### Decisive source
```python
# _output.py:1101-1106 — unknown kinds fail as ordinary ValidationError at the ENVELOPE level
constrained_result = create_model(
    UnionOutputResult.__name__, __base__=UnionOutputResult, kind=(Literal[tuple(self._processors)], ...))

# _output.py:1238-1249 — the ladder: trust kind if the value still matches; else re-resolve by type;
# else pass through unmodified (the output function does NOT run)
kind: str | None = state
if kind is not None:
    inner = self._processors[kind]
    if self._semantic_matches_inner(inner, semantic):
        return await self.call(_UnionValidatedOutput(kind=kind, data=semantic), ...)
    # Type mismatch — hook returned a different union member than validation resolved.
    # Fall through to resolve-by-type so we reach the right inner processor.
match = self._resolve_inner_for_value(semantic)
if match is not None:
    return await self.call(match, ...)
return semantic
```

**Flow:** Envelope validated once against the constrained-kind model → inner processor validates `data` → unwrap to semantic → capability hooks may transform → execute: (1) trust the resolved kind while `_semantic_matches_inner` holds (isinstance vs `inner.output_type`, or plain dict for multi-arg functions); (2) on mismatch, scan inners in declaration order for an isinstance match — SKIPPING multi-arg function members because their `output_type` is just the first arg's type and would mis-capture dicts; (3) no match → return the value untouched. Member schemas are merged with `$defs` dedup; titles/descriptions preserved onto each discriminator branch.
**Invariant:** The kind discriminator is validated as a Literal so bogus kinds never reach the `_processors` lookup as KeyError. Multi-arg output functions can only be dispatched via the kind-trust path — the type-scan fallback must skip them (regression test documents the silent-bypass bug this prevents).
**Probe:** `tests/test_capabilities.py::TestUnionOutputProcessorWithHooks::test_union_with_multi_arg_output_function_runs` (:21532), `::test_union_resolve_by_type_skips_multi_arg_inners` (:21556), `::test_union_on_output_validate_error_fires` (:21602).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "UnionOutputProcessor _UnionValidatedOutput resolve_inner_for_value", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the three-rung dispatch ladder (kind-trust → type-scan skipping multi-arg → passthrough) and Literal-constrained discriminators; adapt member naming to your schema generator; omit rung 2 entirely if your hooks cannot change types. Caveat: source read at HEAD this session.
