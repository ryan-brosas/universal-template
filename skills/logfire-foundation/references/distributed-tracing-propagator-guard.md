<!-- capsule-v2 -->
# Distributed-tracing propagator guard — how does the SDK warn about unintentional cross-service trace joins without breaking extraction?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What are the three distributed_tracing modes, how are they layered onto the global textmap, and how does attach_context bypass or respect them?

## WarnOnExtract / NoExtract propagators + configure wiring
**Path/Symbol:** `logfire/propagate.py:WrapperPropagator family` (`propagate.py:99-161`) + installation in `config.py:_initialize` (`config.py:1588-1597`).
**Signature:** `WarnOnExtractTraceContextPropagator(wrapped, warned=False)`; `NoExtractTraceContextPropagator(wrapped)`; unwrap loop `while isinstance(current_textmap, (Warn…, NoExtract…)): current_textmap = current_textmap.wrapped`.
**Data Shape:** global textmap becomes `Guard(current_real_propagator)`; guard state is per-instance mutable (`warned` flips once).

### Decisive source
```python
current_textmap = get_global_textmap()
while isinstance(current_textmap, (WarnOnExtractTraceContextPropagator, NoExtractTraceContextPropagator)):
    current_textmap = current_textmap.wrapped          # never nest guards on reconfigure
if self.distributed_tracing is None:
    new_textmap = WarnOnExtractTraceContextPropagator(current_textmap)
elif self.distributed_tracing:
    new_textmap = current_textmap                       # silent normal extraction
else:
    new_textmap = NoExtractTraceContextPropagator(current_textmap)
set_global_textmap(new_textmap)
```
Warn fires ONCE when extraction actually changed the span: `if not self.warned and result != context and trace.get_current_span(context) != trace.get_current_span(result)` — then warns AND emits `logfire.warn(message)` so it's visible in telemetry too. NoExtract re-wraps the CURRENT span into fresh context ("spans created within will have the current span as their parent, as if this span didn't exist"). First-party `logfire.attach_context(carrier)` UNWRAPS guards ("while isinstance(propagator, …): propagator = propagator.wrapped") because explicit opt-in isn't accidental; `third_party=True` libraries respect the user's guard instead.
**Flow:** default configure (None) wraps global propagator in warn-mode → first incoming trace headers join traces with a single warning → user chooses True (silence) or False (extraction suppressed but local parenting preserved) → reconfigure unwraps any previous guard first so modes replace rather than stack.
**Invariant:** Guard idempotence across re-configures depends entirely on the unwrap loop. The warn condition must compare SPANS not just contexts (empty-context edge). Explicit attach_context must bypass the guard or first-party propagation would trigger its own warning.
**Probe:** `tests/test_propagation.py` (+ test_configure distributed-tracing cases) — pins warn-once and suppression semantics.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "NoExtractTraceContextPropagator WarnOnExtractTraceContextPropagator attach_context distributed_tracing", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapping-guard pattern for any global hook that needs mode flips without nesting artifacts. Adapt carrier formats freely. Omit the third_party branch if you expose no library-facing API.
