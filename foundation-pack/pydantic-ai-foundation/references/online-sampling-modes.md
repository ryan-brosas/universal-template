<!-- capsule-v2 -->
# Online-eval sampling — how do per-evaluator sample rates interact across evaluators for ONE production call, and how do sampling failures stay non-fatal?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter attaching several evaluators to live traffic must decide whether each evaluator flips its own coin or shares one seed, and what happens when a dynamic `sample_rate` callable raises before the wrapped function runs.

## Per-call shared seed + independent/correlated modes
**Path/Symbol:** `pydantic_evals/pydantic_evals/_online.py:_resolve_sample_rate_field/_resolve_sample_rate/_should_evaluate/sample_evaluators` (:189-260); `pydantic_evals/pydantic_evals/online.py:SamplingMode/SamplingContext` (:93-130).
**Signature:** `sample_evaluators(online_evals: Sequence[OnlineEvaluator], config: OnlineEvalConfig, inputs: Any) -> list[OnlineEvaluator]`; `_should_evaluate(rate, sampling_context, sampling_mode) -> bool`.
**Data Shape:** Sampling happens BEFORE the wrapped function runs. `SamplingContext` carries evaluator, inputs, config metadata, and one per-call `call_seed: float` in [0,1) generated once per call and shared by every evaluator of that call; output and duration are explicitly unavailable at sampling time (docstring contract).

### Decisive source
```python
def sample_evaluators(online_evals, config, inputs):
    call_seed = random.random()          # ONE seed per decorated call
    sampled = []
    for online_eval in online_evals:
        sampling_context = SamplingContext(evaluator=..., inputs=inputs,
                                           metadata=config.metadata, call_seed=call_seed)
        try:
            if _should_evaluate(_resolve_sample_rate_field(online_eval, config),
                                sampling_context, config.sampling_mode):
                sampled.append(online_eval)
        except Exception as exc:
            handler = (online_eval.on_sampling_error if online_eval.on_sampling_error is not None
                       else config.on_sampling_error)
            if handler is not None:
                try: handler(exc, online_eval.evaluator)
                except Exception: pass   # handler exceptions suppressed; evaluator skipped
            else:
                raise                    # no handler → propagates to the caller
    return sampled

# _should_evaluate core:
if isinstance(resolved, bool): return resolved
if resolved >= 1.0: return True
if resolved <= 0.0: return False
if sampling_mode == 'correlated':
    return sampling_context.call_seed < resolved   # subset property
return random.random() < resolved                  # independent (default)
```

**Flow:** `sample_rate=None` resolves to `config.default_sample_rate` LATE (per call, so post-decoration config changes take effect) → callable invoked with `SamplingContext` → bool used directly → float short-circuits at 0/1 → mode decides: `'correlated'` compares the shared `call_seed` against each rate (lower-rate evaluators' calls are always a SUBSET of higher-rate ones; P(any overhead) = max(rate_i)); `'independent'` (default) draws a fresh random per evaluator (P(any) = 1−(1−r)^N).
**Invariant:** In correlated mode the subset property must hold for ANY rate pair on the same call — a porter who draws an independent random per evaluator silently breaks it (and inflates total overhead to the union probability). The error ladder order is fixed: per-evaluator handler → config handler → propagate; a raising handler never crashes the call but DOES skip the evaluator.
**Probe:** `tests/evals/test_online.py::test_correlated_sampling_subset_property` (:1851-1879) seeds `_online.random` and asserts low-rate calls ≤ high-rate calls over 100 invocations; `test_correlated_sampling_max_overhead` (:1883-1909) pins equal call counts across three same-rate evaluators (~10% not ~27% of 200); `test_sample_rate_callable_exception_calls_on_sampling_error` (:1061-1084) and `test_on_sampling_error_handler_exception_suppressed` (:1088-1106) pin the skip-vs-propagate ladder.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "sample_evaluators _should_evaluate call_seed correlated", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of _online.py :189-260 and online.py :93-130 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the one-seed-per-call design with the two named modes — it is the whole trick that makes correlated sampling a subset guarantee instead of a hope. Adopt the three-tier sampling-error ladder (per-evaluator → config → propagate) and the late-bound default rate. Adapt the `random` module seam (tests monkeypatch `_online.random`) to your host's injectable RNG. Omit the trio-specific branches; they only matter if your host supports multiple async libraries. Coverage caveat: none — both files read whole this pass.
