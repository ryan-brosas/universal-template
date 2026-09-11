<!-- capsule-v2 -->
# Runtime trace-block span ladder — one config object names, kinds, and attributes every runtime span

**Source:** Microsoft semantic-kernel MIT `main@b39d95a34435f4c1d55dd00c86120ce118d847e1`; Codebase Memory `semantic-kernel`. **Question:** Where do runtime spans attach, what names/kinds do they get, and why are consumer spans linked instead of parented?

## TraceHelper.trace_block + MessageRuntimeTracingConfig
**Path/Symbol:** `python/semantic_kernel/agents/runtime/core/telemetry/tracing.py:TraceHelper.__init__` (lines 26–40), `trace_block` (43–102); `telemetry/tracing_config.py:MessageRuntimeTracingConfig` (96–201); `in_process/in_process_runtime.py` call sites 235, 274, 345, 376, 429, 466, 497, 549, 590.
**Signature:** `trace_block(operation, destination, parent, *, extraAttributes=None, kind=None, attributes=None, ...) -> ContextManager[Span]`; `build_attributes(operation, destination, extraAttributes) -> dict`; `get_span_name(operation, destination) -> str`; `get_span_kind(operation) -> SpanKind`.
**Data Shape:** `MessagingOperation = Literal["create", "send", "publish", "receive", "intercept", "process", "ack"]`; `MessagingDestination = AgentId | TopicId | str | None`; `ExtraMessageRuntimeAttributes = TypedDict{message_size?, message_type?}`. `TraceHelper` is generic over (Operation, Destination, ExtraAttributes) so a different runtime reuses the ladder with its own literal set.

### Decisive source
```python
# TraceHelper.__init__ — provider ladder:
self.tracer_provider = tracer_provider or get_tracer_provider() or NoOpTracerProvider()
self.tracer = self.tracer_provider.get_tracer(f"agent_runtime {instrumentation_builder_config.name}")

# MessageRuntimeTracingConfig.get_span_kind:
if operation in ["create", "send", "publish"]:
    return SpanKind.PRODUCER
if operation in ["receive", "intercept", "process", "ack"]:
    return SpanKind.CONSUMER
return SpanKind.CLIENT

# get_span_name: f"{NAMESPACE} {operation} {destination_str}"  →  "agent_runtime send type.(key)-A"
# _get_destination_str: AgentId → f"{type}.({key})-A"; TopicId → f"{type}.({source})-T"
```

**Flow:** The runtime constructs ONE `TraceHelper(tracer_provider, MessageRuntimeTracingConfig("InProcessRuntime"))` (in_process_runtime.py 182). Every span site is a `with self._tracer_helper.trace_block(...)` wrapper: `create` with `parent=None` around envelope construction (235/274) — the ONLY span that seeds the trace; `send`/`publish` with `parent=envelope.metadata` around dequeue processing (345/429); nested `process` around the actual handler call (376/466); `ack` around response-future resolution (497); `intercept` around each intervention handler (549/590). Attributes merge in a fixed order: caller `attributes` first, then config `build_attributes` (messaging.operation + messaging.destination + optional message_size/message_type) — config wins on collision. Because each `_process_*` runs in a detached task, the `process` span's parent comes from ambient context propagation inside that task, while the envelope's metadata supplies the LINK back to the producer (see runtime-telemetry-context-propagation).
**Invariant:** Span identity is fully derived from the config object — name template, kind table, attribute builder — so a port changes spans by subclassing TracingConfig, not by touching call sites. The provider ladder (param → global → NoOp) means tracing is always safe with zero setup.
**Probe:** `python/tests/unit/agents/runtime/test_runtime.py` lines 85–125 (`MyTestExporter.exported_spans` + `tracer_provider` fixture); `test_register_receives_publish` (line 175) drives create→publish→process spans through the real SDK TracerProvider — the same harness used to assert span emission in this file.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "semantic-kernel", query: "TraceHelper trace_block MessageRuntimeTracingConfig get_span_kind build_attributes messaging.operation", limit: 10, fields: ["signature", "name", "file"] });
```
(Not executable this pass — MCP surface absent; query kept byte-for-byte for the next connected pass.)

## Verdict
Adopt: the config-object span ladder (name/kind/attributes derived from one generic TracingConfig) plus the create→send/publish→process→ack operation vocabulary for any messaging runtime. Adapt: the operation literal set to your transport's verbs; keep PRODUCER/CONSUMER mapping table-driven. Omit: the `intercept` spans if you have no intervention-handler layer; the camelCase `extraAttributes` kwarg (rename to snake_case in a port).
