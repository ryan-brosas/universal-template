<!-- capsule-v2 -->
# EvaluatorContextSource replay protocol — how do you design a stored-context source so single-fetch is free and batch order is the contract?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255` (pydantic_evals); Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter building offline REPLAY of evaluators over stored production traces (Logfire, an in-house span store) must define the context-source contract: which method does a backend implement, how is single-fetch derived from batch-fetch, and what keeps N spans paired with the right N contexts?

## Protocol with a concrete default method; order lives in the docstring
**Path/Symbol:** `pydantic_evals/pydantic_evals/online.py:EvaluatorContextSource` (:269-297); consumer `run_evaluators` (:300-335, see run-evaluators-ordered-fanout); test mock `MockContextSource` (`tests/evals/test_online.py` :134-144).
**Signature:** `class EvaluatorContextSource(Protocol)` — `async def fetch(self, span: SpanReference) -> EvaluatorContext` (CONCRETE body); `async def fetch_many(self, spans: Sequence[SpanReference]) -> list[EvaluatorContext]` (abstract `...`).
**Data Shape:** input is `SpanReference{trace_id: str, span_id: str}` only — no full span data crosses the boundary, keeping the protocol storage-backend-agnostic; output is full `EvaluatorContext` objects (inputs/output/metadata/duration/attributes/metrics/_span_tree).

### Decisive source
```python
class EvaluatorContextSource(Protocol):
    """Protocol for retrieving stored evaluator contexts.

    Implementations reconstruct [`EvaluatorContext`][...] objects from stored
    traces (e.g., Logfire). The batch method allows fetching contexts for
    multiple spans in a single call.
    """

    async def fetch(self, span: SpanReference) -> EvaluatorContext:
        return (await self.fetch_many([span]))[0]     # single-fetch DERIVED from batch

    async def fetch_many(self, spans: Sequence[SpanReference]) -> list[EvaluatorContext]:
        """... Returns: Evaluator contexts in the same order as the input spans."""
        ...
```

**Flow:** a backend implements ONLY `fetch_many` (one round trip per batch); `fetch` is a protocol-level default that wraps its argument in a one-element list and takes `[0]`. Replay flow = `ctx = await source.fetch(span)` → `results, failures = await run_evaluators(evaluators, ctx)` — no sampling, no sinks, no background dispatch (contrast online-dispatch-sink-grouping's fire-and-forget kernel).
**Invariant:** three rules: (1) the ORDER contract ("contexts in the same order as the input spans") is docstring-only — there is NO runtime check, so a backend returning contexts in completion order silently mis-pairs spans to contexts; positional correspondence is what the tests pin; (2) the protocol is duck-typed (Protocol, not ABC) — implementations are never isinstance-checked, so the mock and any Logfire adapter coexist without registration; (3) only span IDs cross the boundary — the source owns all trace storage, the eval plane never sees raw spans here.
**Probe:** `tests/evals/test_online.py::test_context_source_fetch_many` (:824-843): two spans → `contexts[0].inputs == {'q': '1'}` / `contexts[1].inputs == {'q': '2'}` (positional pairing asserted); `test_context_source_fetch` (:800-820): single fetch returns all fields intact (inputs/output/metadata/duration); `test_fetch_and_run_evaluators` (:846-860): end-to-end fetch → run_evaluators yields 2 results / 0 failures. Suite EXECUTED GREEN at pin this pass (see verification.md).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "EvaluatorContextSource fetch_many SpanReference", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of online.py :269-297 + test_online.py :134-144/:800-860 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the derived-default-method shape for any dual single/batch retrieval protocol — the backend pays for one implementation and the single path cannot drift from the batch path. Adopt the ID-only boundary (references in, full objects out) so the eval plane stays storage-agnostic. Adapt: if your backend genuinely cannot preserve input order (e.g. sharded lookups), make the contract explicit by returning a mapping keyed by span id instead — do not inherit a docstring-only order promise you cannot keep. Omit the protocol entirely if replay is out of scope; `run_evaluators` works on any hand-built context. Coverage caveat: none — both methods read whole at pin.
