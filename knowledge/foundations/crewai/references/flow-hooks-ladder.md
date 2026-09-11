<!-- capsule-v2 -->
# Flow hooks interception ladder — EXECUTION_START/INPUT/PRE_STEP/POST_STEP/OUTPUT/EXECUTION_END with payload rewrite

**Source:** crewAI MIT `main@9e9a8577`; Codebase Memory `ext-crewAI`. **Question:** Where exactly can host code observe/mutate a flow run — and which aliasing/pairing rules make hook rewrites actually stick?

## Connected graph-selected seam
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` — boundary dispatches (:2199-2231), PRE_STEP + positional-arg reverse mapping (:2845-2874), POST_STEP (:2903), OUTPUT/EXECUTION_END (:2417-2433); machinery in `hooks/dispatch.py` (InterceptionPoint, HookAborted).
**Signature:** `dispatch(InterceptionPoint, ctx) -> None` raising `HookAborted` on deny; contexts expose `.payload` as the single mutable channel.
**Data Shape:** step params serialized as `{"_0": arg0, ..., **kwargs}`; hook edits read back through the SAME dict.

### Decisive source
```python
# :2196 inputs ALIASES payload so in-place edits survive read-back
boundary_ctx: InterceptionContext = ExecutionStartContext(
    flow=self,
    inputs=inputs if inputs is not None else {},
    payload=inputs)
...
# :2856 reverse the _N mapping after PRE_STEP mutations
positional = sorted((k for k in updated_params
                     if k.startswith("_") and k[1:].isdigit()),
                    key=lambda k: int(k[1:]))
args = tuple(updated_params[k] for k in positional)
kwargs = {k: v for k, v in updated_params.items()
          if not (k.startswith("_") and k[1:].isdigit())}

# :2423 ordering rule stated verbatim:
# "EXECUTION_END runs before FlowFinishedEvent so a HookAborted prevents a
#  spurious finished signal and payload replacement is honored"
execution_end_dispatched = True     # set BEFORE dispatch: an aborting END hook
dispatch(InterceptionPoint.EXECUTION_END, end_ctx)   # must not re-trigger failure
```

**Flow:** kickoff: EXECUTION_START → INPUT (both may replace payload; abort stamps state id, opens scope, re-raises so failure pairs with opener :2215) → per method: PRE_STEP (may edit args/kwargs via `_N` mapping) → execute → POST_STEP (may replace result) → run end: OUTPUT → EXECUTION_END → FlowFinishedEvent last. Baggage (`flow_inputs`) is REPUBLISHED after the INPUT hook so trigger-payload injection sees rewritten inputs.
**Invariant:** `execution_end_dispatched` flips BEFORE the dispatch call — otherwise a raising END hook would fire `_dispatch_execution_end_failure` for an execution that already ended (double-dispatch). The aliasing comment ("not a fresh {} from or") is load-bearing: replacing inputs wholesale breaks hook chains.
**Probe:** `grep -c 'dispatch(InterceptionPoint.PRE_STEP' lib/crewai/src/crewai/flow/runtime/__init__.py` → `1`; direct suite: `/tmp/crewai-p1-venv/bin/python -m pytest tests/test_flow_ask.py -q -p no:xdist -o addopts=''` → `48 passed` (ask/context plumbing rides the same contextvars set here).
**Direct test:** `tests/test_flow.py::test_flow_with_exceptions` (:480); trigger-payload family :772-897 pins injection-vs-missing-parameter arms.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "execute a method and emit events pre step post step", limit: 5 });
// → ext-crewAI...flow.runtime.Flow._execute_method Method 2812+
```

## Verdict
Adopt the six-point interception lattice + payload-aliasing + end-before-finished-event ordering. Adapt hook names. Omit CrewAI's specific ExecutionStart/Input context classes if host has a middleware stack.
