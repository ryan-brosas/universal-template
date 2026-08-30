<!-- capsule-v2 -->
# Call-span argument recording — how do you decide WHICH function arguments land on the call span, and how do bad configs fail before the first call?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter adding "record the inputs of this decorated function" to an eval/observability decorator must decide when validation happens (decoration vs call time), what the default records, and how a subset selection is expressed and enforced.

## One capture, two consumers; resolution at decoration time
**Path/Symbol:** `pydantic_evals/pydantic_evals/online.py:_capture_inputs/_ExtractedArgs/_resolve_extract_args/_select_recorded_inputs` (:338-379); decoration-time call site `OnlineEvalConfig.evaluate.decorator` (:577-587).
**Signature:** `_capture_inputs(sig: inspect.Signature, args: tuple[Any, ...], kwargs: dict[str, Any]) -> dict[str, Any]`; `_resolve_extract_args(func, sig, extract_args: bool | Iterable[str]) -> _ExtractedArgs`; `_select_recorded_inputs(inputs: dict[str, Any], extract_args: _ExtractedArgs) -> dict[str, Any] | None`.
**Data Shape:** `_ExtractedArgs = Literal[False, True] | tuple[str, ...]` — the resolved form. The raw input is `False` (record nothing, the DEFAULT), `True` (record all), a bare string (one arg), or any iterable of names.

### Decisive source
```python
def _capture_inputs(sig, args, kwargs):
    bound = sig.bind(*args, **kwargs)
    bound.apply_defaults()
    return dict(bound.arguments)          # ALL bound args, captured once per call

def _resolve_extract_args(func, sig, extract_args):   # runs at DECORATION time
    if extract_args is False or extract_args is True:
        return extract_args
    if isinstance(extract_args, str):
        names = (extract_args,)           # bare string = one-element sugar
    else:
        names = tuple(extract_args)
    if not names:
        return False                      # empty iterable collapses to "record nothing"
    unknown = [name for name in names if name not in sig.parameters]
    if unknown:
        raise ValueError(f'extract_args references parameters not in {func.__qualname__}: {sorted(unknown)}')
    return names

def _select_recorded_inputs(inputs, extract_args):    # runs at CALL time
    if extract_args is False:
        return None                        # no attributes at all
    if extract_args is True:
        return inputs
    return {name: inputs[name] for name in extract_args if name in inputs}
```

**Flow:** `sig.bind + apply_defaults` captures every bound argument into one plain dict BEFORE sampling, so `sample_rate` callables and span recording consume the same object. `extract_args` is normalized once at decoration (bool passthrough → str→1-tuple → iterable→tuple → empty→False → unknown-name ValueError naming the qualname and sorted offenders); at each call, selection maps the resolved form onto the captured dict, with a defensive `if name in inputs` re-filter even though decoration already validated.
**Invariant:** Configuration errors fail at DECORATION time (import time), never mid-call — a typo'd argument name must crash the app before traffic arrives, not drop attributes silently per request. The default records NOTHING (privacy-by-default): `extract_args=False` yields `None`, i.e. zero span attributes, not an empty dict.
**Probe:** `tests/evals/test_online.py::test_extract_args_unknown_parameter_raises` (:2278-2284) pins the decoration-time ValueError; `test_extract_args_accepts_single_string` (:2289-2305) pins str-as-one-element with `'secret' not in attrs`; `test_extract_args_empty_iterable_records_nothing` (:2310-2324) pins empty→False; `test_call_span_default_name_and_no_args` (:2131-2147) pins the default recording nothing (`'x' not in attrs`); `test_call_span_extract_args_subset` (:2173-2189) pins subset selection.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_resolve_extract_args _capture_inputs _select_recorded_inputs", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of online.py :338-379 and :577-587 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the split between decoration-time RESOLUTION (validate names against the signature, normalize forms, fail loud) and call-time SELECTION (map resolved form onto the freshly bound args) — it is what makes misconfiguration a startup error instead of a per-request data leak or silent drop. Adopt privacy-by-default (`False` records nothing) and the empty-iterable-collapses-to-False rule so `extract_args=()` cannot be a foot-gun. Adapt the `inspect.Signature` binding to your host's parameter introspection. Omit the logfire-specific serialization concerns — see `call-span-logfire-gate.md`. Coverage caveat: none — online.py read whole this pass.
