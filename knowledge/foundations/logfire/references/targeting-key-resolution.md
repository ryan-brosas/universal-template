<!-- capsule-v2 -->
# Targeting key resolution — how does deterministic rollout selection choose its key when the caller passes none?

**Source:** logfire MIT `main@e484a6b5`; Codebase Memory `ext-logfire`. **Question:** What is the precedence among explicit keys, nested targeting contexts, and trace-derived keys, and how do attributes merge?

## _get_result_and_record_span targeting ladder + targeting_context CM
**Path/Symbol:** `logfire/variables/variable.py:_get_result_and_record_span` (`variable.py:886-943`) + `targeting_context` (`variable.py:1220-1290`) + `_get_merged_attributes` (`variable.py:836-854`).
**Signature:** `targeting_context(targeting_key: str, variables: Sequence[Variable] | None = None)`; effective key = call-site arg → contextvar by_variable → contextvar default → `'trace_id:{trace_id:032x}'`.
**Data Shape:** `_TargetingContextData{default: str|None, by_variable: dict[str,str]}` in ContextVar; merged attributes order: resource < baggage < user.

### Decisive source
```python
merged_attributes = self._get_merged_attributes(attributes)
# Apply in order of lowest to highest priority:
# resource attributes < baggage < user-provided attributes
if targeting_key is None:
    targeting_key = _get_contextvar_targeting_key(self.name)
if targeting_key is None and (current_trace_id := get_current_span().get_span_context().trace_id):
    # If there is no active trace, the current_trace_id will be zero
    targeting_key = f'trace_id:{current_trace_id:032x}'
...
span_name = f'Resolve variable {self.name}'
# Don't inline the f-string to avoid f-string magic.  <-- deliberate!
```
Context nesting: new data merges with current ("Variable-specific targeting always takes precedence over the default, regardless of nesting order"); `_get_contextvar_targeting_key` returns `ctx.by_variable.get(variable_name, ctx.default)`.
Resolution instrumentation: optional span gated by `variables.instrument` records name/value(JSON-or-repr)/label/version/reason plus composed_from serialized recursively; exceptions recorded on the span.
**Flow:** enter `targeting_context('user123')` → all gets inside inherit default; `targeting_context('org456', variables=[org_var])` nests → org_var sees org456 while others see user123 → outside any context and no explicit key, the CURRENT TRACE id becomes the key (same trace ⇒ same rollout bucket ⇒ consistent behavior within one request).
**Invariant:** The zero-trace-id check matters: OTEL returns 0 when no active span, and 'trace_id:000…0' would silently pin every untraced process to one bucket. Variable-name prefix in the span name is chosen "to make the span name more useful… also prevents it from being scrubbed from the message."
**Probe:** `tests/test_variables/test_targeting.py` — pins nesting precedence and trace-id derivation.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-logfire", query: "targeting_context _get_contextvar_targeting_key _get_merged_attributes", limit: 8, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the four-rung key ladder and attribute merge order for any experiment/rollout system. Adapt the contextvar plumbing to your framework. Omit span-recording details if resolution isn't traced in your port.
