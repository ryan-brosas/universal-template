<!-- capsule-v2 -->
# Model-name suggestion ladder — how do you turn a typo'd provider model id into a "did you mean" without lying?

**Source:** pydantic-ai Apache-2.0 @ `fde1bbb6aff461769a1d6d2440c33c232bf90f03`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** How do you suggest the closest known model name across two failure surfaces (local parse vs provider 404) with honest confidence?

## model-name-suggestion-ladder
**Path/Symbol:** `pydantic_ai_slim/pydantic_ai/models/__init__.py:` `_suggest_known_model_name` (:1460–1475), `_suggest_known_model_id_from_provider_error` (:1478–1494), integration in `infer_model` (:1550, :1559); carrier field `exceptions.py` `ModelHTTPError.suggested_model_id` (:542–571 incl. `__reduce__`/`__setstate__`); Anthropic detection `models/anthropic.py::_map_api_errors` (:323–340).
**Signature:** `_suggest_known_model_name(model, model_name, known_model_ids=None) -> str | None`; `_suggest_known_model_id_from_provider_error(model_id_namespace, model_name) -> str | None`.
**Data Shape:** known ids sorted `(not startswith('gateway/'), name)` — gateway pseudo-models demoted so real models win ties.

### Decisive source
```python
normalized_ids = [k.replace(':', '-', 1) for k in known_ids if ':' in k]   # 'openai:gpt-x' → 'openai-gpt-x'
if matches := get_close_matches(normalized_model, normalized_ids, n=1, cutoff=0.9):
    return next(k for k in known_ids if k.replace(':', '-', 1) == matches[0])
known_names = [k.split(':', maxsplit=1)[1] for k in known_ids if ':' in k]
matches = get_close_matches(model_name, known_names, n=1, cutoff=0.8)
if not matches:
    matches = get_close_matches(normalized_model, known_names, n=1, cutoff=0.7)
if matches:
    return next(k for k in known_ids if k.endswith(f':{matches[0]}'))
return None
```

**Flow:** Surface A (local): `infer_model` fails parse/unknown-provider → append `. Did you mean '{suggested}'?` to the UserError. Surface B (provider): Anthropic maps `not_found_error` with EXACT body message `f'model: {model_name}'` → suggestion computed against ONLY that namespace's ids → rides `ModelHTTPError.suggested_model_id` → message appends `. Did you mean {id!r}?`. Pickling round-trips via `__reduce__`/`__setstate__` which REBUILDS the message suffix on unpickle.
**Invariant:** six rules:
1. Provider-confirmed path uses a HINT FIELD, not a new exception type — docstring rationale is load-bearing: only some model classes have a not-found signal; "a hint that is sometimes absent degrades harmlessly; an exception type that is sometimes absent misclassifies."
2. Detection requires exact `error.type == 'not_found_error'` AND exact `error.message == f'model: {model_name}'` — never guess from generic 404s.
3. Namespace-scoped candidates for provider errors (prefix filter), global list for local errors.
4. Three-rung confidence ladder with DESCENDING cutoffs (0.90 qualified-id → 0.80 bare-name → 0.70 normalized bare-name); first hit wins; None = silence, never a low-confidence guess.
5. `suggestion != model_id else None` — echoing the input back is not a suggestion.
6. Pickle contract: state dict carries raw fields; message decoration reapplied in `__setstate__` (message is derived data).
**Probe:** `tests/test_model_name_suggestions.py::test_model_name_suggestion` (VCR-cassette parametric matrix :167+, e.g. `gpt-5.2-proo` → expected_suggestion) + `::test_inferred_model_name_suggestion` (:238+); gateway variant `tests/test_gateway_model_name_suggestions.py`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "suggest_known_model_name get_close_matches suggested_model_id infer_model", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt ladder + namespace scoping + hint-not-type + pickle-rebuild for any "did you mean" over a curated registry; adapt cutoffs/canonicalization; omit the provider-detection arm where providers don't return machine-readable not-found bodies.
