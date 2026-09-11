<!-- capsule-v2 -->
# TextStreamPart → UIMessageChunk conversion — how does the model-event stream become wire chunks, and where do undefined outputs and provider errors get special treatment?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do you translate an internal streaming event vocabulary into a client chunk protocol without leaking internals or losing terminal states?

## toUIMessageChunk
**Path/Symbol:** `packages/ai/src/ui-message-stream/to-ui-message-chunk.ts:toUIMessageChunk` (:30-387 whole, pure function — one part in, zero-or-one chunk out).
**Signature:** `(part: TextStreamPart<TOOLS>, {tools?, sendReasoning=true, sendSources=false, sendStart=true, sendFinish=true, onError, messageMetadata?, responseMessageId?}): InferUIMessageChunk | undefined`.

### Decisive source
```ts
case 'tool-result': {
  return {
    type: 'tool-output-available', toolCallId: part.toolCallId,
    // UI stream chunks are serialized as JSON, which drops undefined
    // properties. Use null so tool outputs always keep the output field.
    output: part.output === undefined ? null : part.output,
    ...(part.preliminary != null ? { preliminary: part.preliminary } : {}),
    ...
  };
}
case 'tool-error': {
  errorText: part.providerExecuted
    ? typeof part.error === 'string' ? part.error : JSON.stringify(part.error)  // provider data: verbatim
    : onError(part.error);                                                       // local tool: sanitized
}
case 'tool-call': if (part.invalid) → 'tool-input-error' (errorText: onError(part.error));
case 'tool-input-end': case 'raw': return undefined;   // deliberately NOT representable on the UI wire
default: const exhaustiveCheck: never = partType; throw new Error(`Unknown chunk type: ...`);
```

**Flow:** every TextStreamPart switches here; reasoning parts honor `sendReasoning:false` by returning `undefined` for start/delta/end AND reasoning-file; sources default OFF (`sendSources=false`); start/finish gates (`sendStart/sendFinish`) exist so a host can frame the stream itself; file/reasoning-file parts inline as `data:${mediaType};base64,...` URLs (:130).
**Invariant:** (1) `undefined` output MUST become `null` at the chunk boundary (:281-282 source comment IS the invariant) — JSON.stringify drops undefined keys, and a missing `output` key would make the reducer's state machine treat a completed call as still-waiting. (2) Error-text asymmetry is SECURITY, not style: local tool errors route through `onError` (default hides details), but PROVIDER-executed tool errors serialize their real message/JSON — the server never executed them, so there is nothing local to leak (:297-318). (3) Invalid tool calls degrade to `tool-input-error` chunks carrying best-effort input — the invalid-call visibility contract from pass 4's repair ladder re-expressed on the UI wire. (4) `isDynamic()` re-derives the dynamic flag per part from the tools map, falling back to the part's own flag when the tool isn't listed (provider/dynamic tools aren't in `tools`) (:47-56). (5) `tool-input-end` and `raw` map to `undefined` — porting them through creates chunk types no client schema accepts. (6) The exhaustive `never` check makes adding a new TextStreamPart a COMPILE error here, keeping converter and protocol locked together (:382-385).

**Probe:** `bash -c "grep -n 'so tool outputs always keep the output field' $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/to-ui-message-chunk.ts && grep -c 'isDynamic(part)' $REFERENCE_ROOT/ai/packages/ai/src/ui-message-stream/to-ui-message-chunk.ts"` → `:281` (comment) and `4`.

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "createUIMessageStream handleUIMessageStreamFinish toUIMessageChunk", limit: 5 });
// → ai.packages.ai.src.ui-message-stream.to-ui-message-chunk.toUIMessageChunk Function :30-387
// NOTE twin: packages/workflow/src/to-ui-message-chunk.ts:toUIMessageChunk :11-212 also matches this query.
```

## Verdict
Adopt the undefined→null boundary rule and the two-tier error-text policy exactly. Adapt which parts your wire represents. Omit the exhaustive-check only in dynamically-typed hosts (and accept silent drift).
