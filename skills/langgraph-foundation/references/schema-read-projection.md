<!-- capsule-v2 -->
# Per-node input projection — What state dict does a task actually receive, and who shares it?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `langgraph`. **Question:** Which keys reach a node's input, what happens to empty or unknown channels, and when is the same input object reused across sibling tasks?

## Declared-channels-only view; missing keys vanish; inputs are cached shallow copies
**Path/Symbol:** `libs/langgraph/langgraph/pregel/_algo.py:_proc_input` (:1348-1392), `libs/langgraph/langgraph/pregel/_io.py:read_channels` (:38-53) + `read_channel` (:23-35), container contract `libs/langgraph/langgraph/pregel/_read.py:PregelNode` (:97-151, `input_cache_key` :251-259).
**Signature:** `_proc_input(proc: PregelNode, managed, channels, *, for_execution, scratchpad, input_cache) -> Any` (MISSING sentinel when a str-select channel is unavailable).
**Data Shape:** `proc.channels: str | list[str]`; list-select returns `{key: value}` including ONLY available keys; str-select returns the bare value or MISSING; managed fallback fires per-key when the name is not a real channel.

### Decisive source
```python
    # if in cache return shallow copy
    if input_cache is not None and proc.input_cache_key in input_cache:
        return copy(input_cache[proc.input_cache_key])
    if isinstance(proc.channels, list):
        val: dict[str, Any] = {}
        for chan in proc.channels:
            if chan in channels:
                if channels[chan].is_available():
                    val[chan] = channels[chan].get()
            else:
                val[chan] = managed[chan].get(scratchpad)   # managed-value arm
    elif isinstance(proc.channels, str):
        if proc.channels in channels:
            if channels[proc.channels].is_available():
                val = channels[proc.channels].get()
            else:
                return MISSING                              # whole task dropped
        else:
            return MISSING
    if for_execution and proc.mapper is not None:
        val = proc.mapper(val)
    if input_cache is not None:
        input_cache[proc.input_cache_key] = val
```

**Flow:** During task preparation each PULL task projects its declared channel set from the frozen step-N channel values: available keys contribute their current value, never-yet-written keys are silently omitted (skip-empty default in `read_channels`), keys naming managed specs compute via `ManagedValue.get(scratchpad)`, and a str-select whose single channel is empty yields MISSING so the caller drops the task entirely. The projected value may pass through `proc.mapper` at execution time. The FIRST computed projection for a given `input_cache_key` is memoized per superstep; siblings with identical subscriptions receive SHALLOW COPIES, not recomputations.
**Invariant:** A node can never observe a channel it did not declare (private-state hiding); inputs reflect the immutable step-N snapshot, never same-step writes (contrast: branch routers read fresh=True); shared projections are read-only by convention because copies are shallow — mutating nested containers leaks across sibling tasks sharing the key.
**Probe:** `python -m pytest tests/test_state.py::test_private_input_schema_conditional_edge -q` (private schema keys hidden from nodes); `grep -n "input_cache\[proc.input_cache_key\]" libs/langgraph/langgraph/pregel/_algo.py` → 2 hits (:1360 copy-out, :1390 memoize).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "langgraph", query: "_proc_input read_channels select input cache", limit: 8 });
```

## Verdict
Adopt declared-only projection with skip-empty reads — it is what makes private state and schema evolution safe under concurrent writers. Adapt MISSING-vs-omit to your host's task-skipping convention but keep them distinct (whole-task drop != absent key). If you reuse projections across tasks, deep-copy or freeze them; shallow copy is a performance choice, not a safety boundary.