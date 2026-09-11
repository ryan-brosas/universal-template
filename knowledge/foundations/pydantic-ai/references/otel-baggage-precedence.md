<!-- capsule-v2 -->
# OTel baggage precedence — how do ambient identifiers (tenant/user) ride onto every evaluation event without corrupting semconv attributes?

**Source:** pydantic-ai MIT `main@a5b5fb7a247f863599d61dfa9159bc2ebc786255`; Codebase Memory `mnt-hdd-utopia-inspo-pydantic-ai`. **Question:** A porter propagating request-scoped identifiers (tenant, user, request id) from the calling context onto every emitted telemetry event must decide when to snapshot the ambient context, how to merge it with the event's own attributes, and who wins on key conflict.

## Snapshot once per dispatch; standard attrs win on conflict
**Path/Symbol:** `pydantic_evals/pydantic_evals/_otel_emit.py:_baggage_attrs` (:105-110), `_base_attrs` (:168-182), `emit_otel_events` include_baggage param (:74, :98); `pydantic_evals/pydantic_evals/online.py:OnlineEvalConfig.include_baggage` docstring (:446-456).
**Signature:** `_baggage_attrs() -> Mapping[str, Any] | None`; `_base_attrs(target, name, source, evaluator_version, baggage_attrs) -> dict[str, Any]`.
**Data Shape:** OTel baggage (a context-propagated key/value map) flattened to `{str(k): v}`; `None` when empty. Merged UNDER the event's own attributes.

### Decisive source
```python
def _baggage_attrs():
    """Snapshot the current OTel baggage as a flat attribute mapping, or None if empty."""
    bag = baggage.get_all()
    if not bag:
        return None
    return {str(k): v for k, v in bag.items()}

def _base_attrs(target, name, source, evaluator_version, baggage_attrs):
    # Apply baggage first so standard attributes always win on conflict.
    attrs: dict[str, Any] = dict(baggage_attrs) if baggage_attrs else {}
    attrs[_ATTR_TARGET] = target
    attrs[_ATTR_EVAL_NAME] = name
    attrs[_ATTR_EVALUATOR_SOURCE] = _serialize_evaluator_source(source)
    if evaluator_version is not None:
        attrs[_ATTR_EVALUATOR_VERSION] = evaluator_version
    return attrs

# emit_otel_events:
baggage_attrs = _baggage_attrs() if include_baggage else None   # ONCE per call, not per event
```

**Flow:** When `include_baggage=True` (the config default), the current OTel baggage is snapshotted ONCE per `emit_otel_events` call — i.e. per evaluator run, shared by every result and failure event in that run — into a flat string-keyed map, or `None` when empty. `_base_attrs` seeds the attribute dict from that snapshot FIRST, then writes the event's own `gen_ai.*` attributes on top, so on any key collision the semconv attribute wins. `include_baggage=False` skips the snapshot entirely, avoiding even the per-run read. End-to-end, baggage set in the calling context (e.g. `tenant=acme`) appears as a plain attribute on each emitted event.
**Invariant:** Baggage can ADD keys but never OVERWRITE `gen_ai.*` or `error.type` — the merge order (baggage first, standard second) is the entire enforcement mechanism, and a hostile or misconfigured upstream context cannot corrupt the semantic-convention fields. The snapshot is per-dispatch, not per-event: all events of one run share one baggage view, so mid-run context mutation cannot split a single evaluation across two identifier sets.
**Probe:** `tests/evals/test_otel_emit.py::test_baggage_attached_to_event_attributes` (:295-310) pins `tenant`/`user_id` landing on the event; `test_baggage_does_not_overwrite_standard_attrs` (:313-329) sets baggage keys `gen_ai.evaluation.target` and `gen_ai.evaluation.score.label` and pins that `'real_target'` and `'pass'` still win; `test_include_baggage_false_skips_snapshot` (:332-347) pins the opt-out; end-to-end twin `tests/evals/test_online.py::test_baggage_attached_to_evaluation_event` (:2400-2421) pins propagation through the full decorated-call path.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pydantic-ai", query: "_baggage_attrs include_baggage _base_attrs baggage.get_all", limit: 10, fields: ["signature", "name", "file"] });
```
Live check this pass: Codebase Memory MCP was unreachable in this session (stdio env reference unavailable at transport open); anchors confirmed by direct read of _otel_emit.py :105-110/:168-182 and online.py :446-456 at pin `a5b5fb7a` (zero drift, clean tree).

## Verdict
Adopt the merge-order-as-enforcement pattern: seed from the ambient snapshot, write your own attributes last, and document that standard names always win — no per-key allowlist needed. Adopt the once-per-dispatch snapshot (shared by all events of a run) and the empty→None short-circuit. Adapt the OTel `baggage` API to your host's ambient-context carrier (ContextVar, thread-local, request scope). Omit nothing here — the plane is small and the precedence rule is the whole value. Coverage caveat: none — both cited files read in full this pass.
