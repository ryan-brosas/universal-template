<!-- capsule-v2 -->
# Variable resolution pipeline — what is the exact priority chain and compose→render→deserialize ladder for managed variables?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** In what order are context overrides, provider values, labels, and code defaults consulted, and how do failures at each stage degrade?

## Variable._resolve_inner + _lookup_serialized + _resolve_code_default_value
**Path/Symbol:** `logfire/variables/variable.py:_resolve_inner` (`variable.py:321-425`), `_lookup_serialized` (`variable.py:486-546`), `_resolve_code_default_value` (`variable.py:647-738`).
**Signature:** `_resolve(targeting_key, attributes, span, label, render_fn) -> ResolvedVariable[T]`; lookup chain shared by composition so "the two paths can't drift".
**Data Shape:** `ResolvedVariable{name, value, label, version, reason, exception, composed_from}`; reasons: resolved / code_default / context_override / validation_error / other_error.

### Decisive source
```python
# Priority chain (_lookup_serialized docstring):
# 1. Context override (only for variables whose type we know)
# 2. Provider (label-specific first, falling back to default targeting)
# 3. Registered code default
provider_result = provider.get_serialized_value_for_label(name, label) if label else provider.get_serialized_value(...)
if provider_result.value is not None: return provider_result
serialized_default = variable._get_serialized_default(targeting_key, attributes)
```
Pipeline per candidate value (`_try_resolve`, strict flag):
```python
serialized_value, composed = expand_references(serialized_value, self.name, resolve_ref, strict=strict)
# ALWAYS runs expand_references even without refs: it also unescapes \@{...}@ —
# gating on has_references made escaped-only values keep their backslash inconsistently
if fatal_error := _first_fatal_composition_error(composed):   # cycles/depth = FATAL
    return _ResolveAttempt(ok=False, exception=..., stage='composition', composed=composed)
if render_fn: ...                                              # {{}} templates; TemplateInputsMismatchError NOT caught
value_or_exc = self._deserialize(serialized_value)             # pydantic TypeAdapter.validate_json
```
Fallback semantics: a PROVIDER value composes STRICTLY (unresolved @{ref}@ ⇒ fall back to code default rather than render empty); the CODE DEFAULT then composes strict → non-strict ("an unresolved @{ref}@ within it renders as an empty string — there is nowhere further to fall back") → raw uncomposed default on structural failure. Soft per-reference failures (missing ref text left in place) deliberately do NOT trigger wholesale fallback.
**Flow:** override fast-path (serializable→pipeline; NON-serializable→returned VERBATIM under reason='context_override' restoring pre-#1951 behavior) → provider/label lookup → strict compose → on failure `_resolve_code_default_value(trigger_exc=…)` which preserves provenance (original label/version/composed chain ride the fallback result).
**Invariant:** Callable defaults are memoised per-get via the `_DEFAULT_CACHE` ContextVar INCLUDING raised exceptions ("a failing default doesn't get called multiple times either"). Warnings use `_emit_resolution_warning` which SWALLOWS `-W error` escalation so filterwarnings=error can't convert an informational warning into a bogus other_error fallback.
**Probe:** `tests/test_variables/test_variable_resolution.py` — pins chain order, strict/non-strict fallback, verbatim-unserializable overrides.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "_lookup_serialized _try_resolve expand_references _resolve_code_default_value", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt: three-tier lookup with label bypass, strict-for-provider vs lenient-for-default composition asymmetry, fatal-vs-soft composition error split, exception-memoised callable defaults. Adapt the JSON validation to your typing stack. Omit template rendering if you don't port Handlebars.
