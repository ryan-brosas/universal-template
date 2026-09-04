<!-- capsule-v2 -->
# Interrupt / resume protocol — How does a node pause mid-body and receive the human's answer on resume?

**Source:** LangGraph MIT `main@f09cfe8ffc1eeffd68f4b628ed69c30f7cad229f`; Codebase Memory `ext-langgraph`. **Question:** How are multiple interrupt() calls in one node matched to resume values, and what happens when resume data is missing or ambiguous?

## Positional resume list per task; None-resume is global; ids required for parallel interrupts
**Path/Symbol:** `libs/langgraph/langgraph/types.py:interrupt` (:851-977), scratchpad construction `libs/langgraph/langgraph/pregel/_algo.py:_scratchpad` (:1280-1347), multi-interrupt guard `libs/langgraph/langgraph/pregel/_loop.py:_first` (:910-928).
**Signature:** `interrupt(value: Any) -> Any` — raises GraphInterrupt on first call; returns the resume value on re-execution.
**Data Shape:** PregelScratchpad holds `interrupt_counter` (LazyAtomicCounter — itertools.count because `+= 1` is not thread-safe), task-scoped `resume: list`, and `get_null_resume(consume)` walking up parent scratchpads for subgraphs.

### Decisive source
```python
idx = scratchpad.interrupt_counter()
# find previous resume values (positional match within THIS task)
if scratchpad.resume:
    if idx < len(scratchpad.resume):
        conf[CONFIG_KEY_SEND]([(RESUME, scratchpad.resume)])
        return scratchpad.resume[idx]
# find current resume value (the global null-task resume)
v = scratchpad.get_null_resume(True)
if v is not None:
    assert len(scratchpad.resume) == idx, (scratchpad.resume, idx)
    scratchpad.resume.append(v)
    conf[CONFIG_KEY_SEND]([(RESUME, scratchpad.resume)])
    return v
# no resume value found — surface to client
raise GraphInterrupt((Interrupt.from_ns(value=value, ns=conf[CONFIG_KEY_CHECKPOINT_NS]),))
```
**Flow:** Node body calls interrupt() → raises with an `Interrupt` carrying ns-derived id → runner.commit persists `(INTERRUPT, payload)` writes → loop exits with status/interrupt surfaced. On `Command(resume=v)`: `_first` maps it to a NULL_TASK RESUME write; re-executed node re-runs from the top; each interrupt() call consumes resume[idx] positionally; the assert guarantees the resume list only grows in lockstep with interrupt order. A dict resume whose keys are ALL xxh3 hex digests becomes a RESUME_MAP (namespace-addressed per-interrupt values); otherwise >1 pending interrupts WITHOUT map ⇒ RuntimeError demanding per-interrupt ids.

**Invariant:** None can never BE a resume value (`get_null_resume` docstring: "difficult to distinguish from missing when used over http") — None means "not resuming". Interrupts are not errors: they ride `GraphBubbleUp`, get persisted as writes, and the loop suppresses them at root exit after emitting `__interrupt__`. Resume re-executes the ENTIRE node body — side effects before interrupt() run twice.

**Probe:** `grep -n 'def interrupt' libs/langgraph/langgraph/types.py` → :851; `grep -n 'get_null_resume(True)' libs/langgraph/langgraph/types.py` → :960; `grep -n 'Interrupt.from_ns' libs/langgraph/langgraph/types.py` → :969. Direct tests: `tests/test_pregel.py:4839 test_interrupt_multiple`, `:5291 test_multiple_interrupt_state_persistence`, `:8906 test_null_resume_disallowed_with_multiple_interrupts`, `:7577 test_parallel_interrupts` (Send fan-out of child graphs each interrupting).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-langgraph", query: "interrupt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt exception-as-control-flow with positional per-task resume lists and the global-null-resume fallback for single-interrupt ergonomics. Adapt id grammar (ns-hash vs explicit ids) to your transport. Omit the legacy NodeInterrupt path (deprecated in favor of this function).
