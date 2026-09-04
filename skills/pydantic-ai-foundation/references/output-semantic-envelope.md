<!-- capsule-v2 -->
# Semantic-value envelope — hooks see `42`, validation sees `{'response': 42}`; who unwraps?

**Source:** pydantic-ai MIT `main@b3cdbc96796f0294f1ac6943cdba70d14af8a0ef`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai` (full mode, coverage clean). **Question:** When output hooks must transform a validated output, what shape do they see — and how does the framework re-enter its internal dict-shaped validation afterwards?

## ObjectOutputProcessor hook_unwrap_key
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/_output.py:ObjectOutputProcessor.hook_unwrap_key` (:964-987), `hook_validate` (:989-999), `hook_execute` (:1001-1014), `_build_output_handlers` closure state (:75-104).
**Signature:** `hook_validate(data, *, run_context, allow_partial=False) -> tuple[Any, Any]` (semantic value, opaque state); `async hook_execute(semantic, state, *, run_context, wrap_validation_errors=True) -> Any`.
**Data Shape:** Internal transport is dict-wrapped (`{'response': 42}` for bare primitives via `outer_typed_dict_key='response'`; single-arg functions via `FunctionSchema.single_field_name`; multi-arg functions and BaseModel outputs are already dicts/objects with NO wrapper). Hooks always receive and return the UNWRAPPED semantic value.

### Decisive source
```python
# _output.py:997-999 — peel the envelope at the hook boundary
validated = self.validate(data, allow_partial=allow_partial, ...)
if (k := self.hook_unwrap_key) is None:
    return validated, None
return validated[k], None

# _output.py:1009-1014 — re-wrap WITHOUT an idempotency check, deliberately
# Re-wrap the (possibly hook-modified) semantic value into the internal dict shape `call()` expects.
# No idempotency check: for `output_type=dict[...]`, the semantic value can itself be a dict
# that happens to contain the unwrap key.
if (k := self.hook_unwrap_key) is not None:
    semantic = {k: semantic}
return await self.call(semantic, run_context=run_context, wrap_validation_errors=wrap_validation_errors)
```

**Flow:** Raw model text/tool-args → processor.validate (markdown fences stripped; JSON-string fallback allowed in the validation TypedDict for sloppy models like Bedrock Meta) → envelope peeled at `hook_validate` → capability chain transforms the SEMANTIC value → `hook_execute` re-adds the wrapper key → internal `call()` unwraps again (`output[k]`), runs any output function. The `(semantic, state)` tuple lets each processor smuggle per-invocation resolution state (union kind, below) through the hook chain without exposing internals.
**Invariant:** The docstring contract on `after_output_validate` states it directly: output hooks see the semantic value "regardless of how it's internally represented during validation" — while TOOL hooks always see raw `dict[str,Any]` args. Re-wrapping must be unconditional: an `isinstance(dict)` guard would corrupt `output_type=dict[str, str]` whose value legitimately contains the key.
**Probe:** `tests/test_capabilities.py::TestOutputHookEdgeCases.test_hooks_on_output_process_via_hooks_class` (:21264); semantic-transform test `::test_hook_transform_at_semantic_boundary` (:22235 — `output * 2` flows through correctly).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "hook_unwrap_key outer_typed_dict_key hook_validate hook_execute", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-shape rule (internal envelope vs hook-facing semantic value) with a single peel/re-wrap boundary pair; adapt the wrapper key name to your host; omit the JSON-string-lenient validation variant if your providers are strict. Caveat: source read at HEAD this session.
