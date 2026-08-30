<!-- capsule-v2 -->
# Stream delta forwarding gate — which SDK events become user-visible deltas, and which die silently?

**Source:** os-clovy MIT `main@8fed7acb51622d36bfaaa056f43931015dfd5d72`; Codebase Memory `os-clovy`. **Question:** A porter bridging an SDK event stream to a UI must decide exactly which raw events surface as text/reasoning deltas without duplicating or fabricating output.

## forwardSdkEvent filter
**Path/Symbol:** `agent-runtime/src/sdk-engine.ts:OpenAIAgentsEngine.forwardSdkEvent` (:378-388); suffix gate `isDeltaEvent` (:750-752). Called once per raw event from `consumeStream` :319 (`for await (const event of stream) this.forwardSdkEvent(event, emit)`).
**Signature:** `private forwardSdkEvent(event: unknown, emit: (event: EngineEvent) => void): void`; `isDeltaEvent(type): type.endsWith(".delta") || type.endsWith("_delta")`.
**Data Shape:** Emits only `{type:"reasoning.delta", delta}` or `{type:"message.delta", delta}` with `delta: string`. Everything else in the SDK event shape is ignored.

### Decisive source
```ts
if (!isRecord(event) || event.type !== "raw_model_stream_event" || !isRecord(event.data)) return;
const type = String(event.data.type ?? "");
const delta = typeof event.data.delta === "string" ? event.data.delta : undefined;
if (!delta) return;                                   // empty/absent delta → silent drop
if (type.includes("reasoning") && isDeltaEvent(type)) {
  emit({ type: "reasoning.delta", delta });
} else if (type.includes("output_text") && isDeltaEvent(type)) {
  emit({ type: "message.delta", delta });
}
```

**Flow:** every SDK stream event passes through one filter: wrong envelope (`raw_model_stream_event` + record `data`) → dropped; non-string or empty `delta` → dropped; remaining candidates must BOTH mention their channel in the event type AND end `.delta`/`_delta`, so terminal events like `output_text.done` or lifecycle bookkeeping never masquerade as content. The service layer then forwards engine events verbatim (`forwardEngineEvent`, service.ts :322-324) — no re-shaping between engine and wire.
**Invariant:** A delta reaches the UI only as a string payload of exactly two event kinds; completion/annotation/metadata events can never render as text; reasoning and message channels are mutually exclusive by the first matching substring. Ordering is the SDK's own emission order — the runtime adds no buffering or coalescing (service.test asserts the monotonic ladder `run.started → message.delta → message.completed → usage.updated → run.completed`).
**Probe:** `agent-runtime/test/service.test.ts` "streams lifecycle events and completion in monotonic order" (:29-44, exact event-sequence array) and :45-77 (identity path emits its fixed reply as a `message.delta`); `agent-runtime/test/sdk-tool-loop.test.ts` :16-57 (identity `message.delta` text asserted verbatim). Suites runner-blocked at pin; ranges read directly.

## Get live surrounding code
**Retrieve:** executed at pin:
```
search_graph({ project:"os-clovy", query:"sdk history runtime items usage normalize", file_pattern:"agent-runtime/src/*" })
→ src.sdk-engine.OpenAIAgentsEngine.forwardSdkEvent Method sdk-engine.ts 378-388
   src.sdk-engine.sdkHistoryToRuntime Function sdk-engine.ts 572-600
   src.sdk-engine.normalizeUsage Function sdk-engine.ts 706-714
```

## Verdict
Adopt the double-gate (envelope check + channel-substring ∧ delta-suffix) and pass-through ordering — it is the minimal filter that cannot invent output. Adapt the two channel substrings and event names to your SDK's vocabulary. Omit any impulse to coalesce or re-chunk here: if your transport needs batching, do it below this gate, because tests pin per-delta emission order.
