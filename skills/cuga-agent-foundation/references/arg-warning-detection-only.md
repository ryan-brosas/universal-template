<!-- capsule-v2 -->
# Detection-only malformed-argument warnings — why log suspect tool kwargs but never coerce them, and why must the wrapper preserve sync-ness?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** Your agent sometimes passes a dict where a scalar is required (dict-as-string bug) — should the tool layer auto-coerce, and how do you instrument without changing behavior?

## Inspect + warn + forward UNCHANGED; sync tools get sync wrappers or you stall the event loop
**Path/Symbol:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/adapter/arg_warning.py` — module docstring :1-10 (the detection-only rationale from eval mining), `_PY_TO_JSONSCHEMA` :21-28, `jsonschema_type` :33-41 (mirrors create_tool_from_api_dict mapping, unwraps Optional), `suspect_reason` :44-66, `warn_suspect_kwargs` :69-87, `make_arg_warning_callable` :90-133. Direct suite: `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_arg_warning.py`.
**Signature:** `suspect_reason(ptype: Optional[str], value) -> Optional[str]`; `warn_suspect_kwargs(kwargs, field_types, *, model_name) -> None`; `make_arg_warning_callable(tool_func, input_model, *, enable: bool) -> Callable`.
**Data Shape:** detects EXACTLY three shapes on scalar params (string/integer/number/boolean): dict-where-scalar, list-where-scalar, stringized int/float (`"42"` for integer). Correct scalars never trigger.

### Decisive source
```python
# :59-65 — bool excluded from stringized-number check (bool subclasses int)
if isinstance(value, str) and ptype in ("integer", "number"):
    try: int(value) if ptype == "integer" else float(value)
    except ValueError: return None
    return f"stringized {ptype}"
```
```python
# :100-108 docstring — the load-bearing sync/async subtlety
# The wrapper preserves the sync/async nature of tool_func ... wrapping a *sync*
# callable in an async def would make it await inline on the event loop instead
# of being dispatched to a worker thread via run_in_executor, so a blocking sync
# tool could stall the loop (a silent, default-on behavior change).
```
**Flow:** disabled or schema-less ⇒ return tool_func untouched → precompute `{field: jsonschema_type(annotation)}` once → wrap preserving coroutine-ness → wrapper fires ONLY when `kwargs and not args` (positional calls left alone to avoid misreading bound arguments) → unknown keys ignored → log `[arg-warning] {model}: '{name}' looks malformed — {reason}; forwarded unchanged` → call through.
**Invariant:** (1) NEVER mutate kwargs — mining showed malformed shapes don't cause agent-visible failures today; coercion would be an unforced behavior change and hide regressions. (2) Sync stays sync (see above) — this interacts with make_tool_awaitable's executor dispatch. (3) Warnings are the regression tripwire: if a future model reintroduces dict-as-string at scale, logs surface it before users do.

**Probe:** `src/cuga/backend/cuga_graph/nodes/cuga_lite/tests/test_arg_warning.py` — pins suspect_reason shapes, kwargs-only gating, and no-mutation.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "warn_suspect_kwargs suspect_reason arg_warning make_arg_warning_callable", limit: 8 });
```
## Verdict
Adopt detect-don't-coerce when eval evidence says mutation is unjustified; adopt the preserve-sync-ness rule EVERYWHERE you wrap tool callables for instrumentation.
