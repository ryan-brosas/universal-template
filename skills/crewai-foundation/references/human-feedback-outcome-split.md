<!-- capsule-v2 -->
# Human-feedback outcome/output split — when a method's return value routes the flow, how does the flow's final output stay the REAL output?

**Source:** crewAI MIT `main@9e9a8577becc322f98a966ad88d7904251049744`; Codebase Memory `ext-crewAI`. **Question:** How can one value drive routing while a different value reaches `method_outputs` and the final result?

## Stash dict swap after method_outputs append
**Path/Symbol:** `lib/crewai/src/crewai/flow/runtime/__init__.py` (`_execute_method` stash :2919–2926; producer `_run_human_feedback_step` :3585–3602; definition canonicalizer `flow_definition.py:686–696`).
**Signature:** `_human_feedback_method_outputs: dict[str, Any]` (PrivateAttr); presence in dict = stashed, not value.
**Data Shape:** with `emit`, `_run_human_feedback_step` returns `result.outcome` as the method's VISIBLE return while stashing `method_output`.

### Decisive source
```python
# For @human_feedback methods with emit, the result is the collapsed outcome
# (e.g., "approved") used for routing. But we want the actual method output
# to be the stored result (for final flow output). Replace the last entry
# if a stashed output exists. Dict-based stash is concurrency-safe and
# handles None return values (presence in dict = stashed, not value).
if method_name in self._human_feedback_method_outputs:
    self._method_outputs[-1]["output"] = (
        self._human_feedback_method_outputs.pop(method_name)
    )
```
```python
if emit:
    # Stash the real method output: the collapsed outcome routes
    # listeners, but the flow's final result stays the method's
    # actual return value.
    self._human_feedback_method_outputs[method_name] = method_output
    return result.outcome
```

**Flow:** emit-decorated methods run review → collapsed outcome returned to the engine so listeners keyed on "approved"/"rejected" fire → real output stashed under the method name → immediately after `_method_outputs.append({outcome})`, the tail entry is REPLACED from the stash in the same synchronous block → definition-level validator force-marks such methods as routers (`router=True, emit=None`) regardless of authoring shape.
**Invariant:** The stash is dict-keyed on METHOD NAME precisely because outcomes may be None or falsy — a sentinel-based design would drop them. Swap happens before any await, so no interleaving listener can observe the outcome-as-output. Resume paths replicate the split via `resumed_method_output`.
**Probe:** `.venv/bin/python -m pytest "lib/crewai/tests/test_flow.py::test_flow_with_router" "lib/crewai/tests/test_flow_definition.py::test_flow_definition_classifies_start_router_from_human_feedback_emit" -q` (expect 2 passed); static anchor: `grep -c "_human_feedback_method_outputs.pop(method_name)" lib/crewai/src/crewai/flow/runtime/__init__.py` → 1 (:2922).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-crewAI", query: "human feedback emit outcome stash method outputs routing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt presence-keyed stash + immediate tail swap; adapt to typed route enums if your labels are structured; omit the definition canonicalizer only for hand-authored definitions. Direct tests executed green at pin.
