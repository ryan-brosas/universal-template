<!-- capsule-v2 -->
# lmp decorator pipeline — how does a plain function become a tracked, provider-calling LMP?

**Source:** ell MIT `main@9d129846203e75efeb4e5cddd3fb1c164dc0b243`; Codebase Memory `ext-ell`. **Question:** What is the full attribute/return contract a decorator must establish so tracking, caching, and provider dispatch all work from one wrapper?

## complex → _track composition
**Path/Symbol:** `src/ell/lmp/complex.py:complex` (:16-92) with `_get_messages` (:96-110) and `_client_for_model` (:112-127); `src/ell/lmp/simple.py:simple` (:7-14).
**Signature:** `complex(model, client=None, tools=None, exempt_from_tracking=False, post_callback=None, **api_params)`; inner `model_call(*prompt_args, _invocation_origin=None, client=None, api_params=None, lm_params=None, **prompt_kwargs) -> Tuple[result, final_api_params, metadata]`.
**Data Shape:** dunder contract set on the wrapper: `__ell_api_params__`, `__ell_func__` (the prompt fn), `__ell_type__=LMPType.LM`, `__ell_exempt_from_tracking`; return is ALWAYS the 3-tuple.

### Decisive source
```python
# complex.py:39-50 and 68-77
res = prompt(*prompt_args, **prompt_kwargs)
messages = _get_messages(res, prompt)
...
merged_api_params = {**config.default_api_params, **default_api_params_from_decorator, **(api_params or {})}
n = merged_api_params.get("n", 1)
...
(result, final_api_params, metadata) = provider.call(ell_call, origin_id=_invocation_origin, logger=_logger if should_log else None)
if isinstance(result, list) and len(result) == 1:
    result = result[0]

result = post_callback(result) if post_callback else result
...
#  These get sent to track. This is wack.
return result, final_api_params, metadata
```

**Flow:** prompt executes FIRST (it's just a function returning str or Message list); `_get_messages` converts a bare str into `[system(docstring)?, user(text)]` — the docstring IS the system prompt only for string-returning prompts; param merge order is config defaults < decorator < call-time; provider resolution via client type (see provider-registry capsule); single-choice lists collapse to the lone element BEFORE post_callback so `simple`'s callback sees a scalar. `simple` then asserts away tool params and installs `post_callback=convert_multimodal_response_to_lstr`, making text-only the outermost contract. `lm_params` raises DeprecationWarning immediately.
**Invariant:** the 3-tuple return shape is what lets `_track` treat LM calls uniformly (`func_to_track(...)[0]` in the no-store path); docstring-as-system applies ONLY when the prompt returned a raw string — list-returning prompts own their system message entirely.
**Probe:** `tests/test_lstr.py` + `tests/test_message_type.py` cover the payload plane this feeds; deterministic anchors from repo root: `grep -n 'post_callback' src/ell/lmp/complex.py src/ell/lmp/simple.py` → :72 (apply), :14 (install); `grep -c 'assert' src/ell/lmp/simple.py` == 3 (tools/tool_choice/response_format vetoes).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-ell", query: "get client for model fallback", limit: 5, fields: ["signature", "name", "file"] });
// rank-1: ext-ell.src.ell.lmp.complex._client_for_model @ src/ell/lmp/complex.py:112-127
```

## Verdict
Adopt prompt-first execution plus the strict dunder/3-tuple wrapper contract. Adapt the docstring-as-system convention to your authoring surface. Omit the `XXX`-flagged dynamic-model-pop quirk (popping "model" out of merged api_params) — pass model explicitly in your port instead of rescuing it from api_params.
