<!-- capsule-v2 -->
# W3C traceparent parsing — how do you recover an OTel parent reference from ambient context without ever raising on malformed input?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter attaching evaluation events to a live agent run needs the run's span as PARENT. The parent arrives as a W3C `traceparent` string in ambient (logfire) context — user code, proxies, and SDK versions can all produce garbage. How do you parse it so that bad input degrades observability instead of breaking the agent run?

## Total parser: None in, None out; strict only where corruption is possible
**Path/Symbol:** `pydantic_evals/pydantic_evals/online_capability.py:_parse_traceparent` (:32-48); call site `OnlineEvaluation.wrap_run` (:143); downstream consumer `_otel_emit.py:build_parent_context` (cited by otel-eval-result-event-contract).
**Signature:** `def _parse_traceparent(traceparent: str | None) -> SpanReference | None` — total function, no exception path.
**Data Shape:** input = W3C `00-{trace_id}-{span_id}-{flags}`; output = `SpanReference{trace_id: str(32), span_id: str(16)}` or None.

### Decisive source
```python
def _parse_traceparent(traceparent: str | None) -> SpanReference | None:
    if traceparent is None:
        return None
    parts = traceparent.split('-')
    if len(parts) != 4:
        return None
    trace_id, span_id = parts[1], parts[2]
    if not trace_id or trace_id == '0' * 32:      # W3C "invalid" sentinel values
        return None
    if not span_id or span_id == '0' * 16:
        return None
    return SpanReference(trace_id=trace_id, span_id=span_id)

# call site (:143) — read OUT OF THE LOGFIRE CONTEXT, not from OTel directly:
span_reference = _parse_traceparent(logfire_api.get_context().get('traceparent'))
```

**Flow:** wrap_run reads the header from logfire's context dict (so the capability works without user code importing OTel), parses it into a SpanReference or None, and passes it into `dispatch_evaluators` → `build_parent_context`: a valid reference becomes a NonRecordingSpan parent for every `evaluator:` span and emitted event; None simply yields NO parent link. The agent run itself never touches the parse result — sampling, dispatch, and re-raise behavior are identical either way.
**Invariant:** three rules: (1) the parser is TOTAL — missing, wrong part count, empty ids, and all-zero ids (the W3C invalid sentinels `'0'*32`/`'0'*16`) all return None; nothing raises; (2) strictness is asymmetric by design — it rejects structure (exactly 4 dash-separated parts) and zero IDs (which would corrupt parenting) but does NOT validate hex charset or the version byte: lenient where the spec is strict, strict only where a bad value would mis-parent events; (3) absence of a parent is a legal steady state — downstream emission must treat `span_reference=None` as "emit unparented", never as an error.
**Probe:** `tests/evals/test_online_capability.py::test_malformed_traceparent_yields_no_span_reference` (:543-570): parametrized over `'malformed'`, `00-{0*32}-…-01`, `00-…-{0*16}-01` → after a full agent.run + wait_for_evaluations, `collector.span_refs == [None]` (run completed, dispatch happened, parent absent); `test_span_reference_with_logfire` (:517-540, @needs_logfire): real captured context → SpanReference with 32-char trace_id / 16-char span_id. Malformed suite EXECUTED GREEN at pin this pass (see verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_parse_traceparent SpanReference online_capability", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of online_capability.py :32-48/:143 + test_online_capability.py :517-570 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the total-parser shape for any ambient-context-derived identifier: return None on every malformed form and let the CONSUMER decide what "no parent" means — the producer of the value must never be able to crash the host operation. Adopt the asymmetric strictness rule: reject exactly the forms that would corrupt the consuming data structure (here: wrong arity, zero IDs), skip cosmetic validation (hex charset, version byte) that only adds rejection surface. Adapt the source of the header (logfire context here; your host's equivalent) but keep the read side-effect-free. Omit entirely if your host gives you a typed span object directly — this seam exists precisely because the value crosses as a raw string. Coverage caveat: none — function + call site + both test suites read at pin.
