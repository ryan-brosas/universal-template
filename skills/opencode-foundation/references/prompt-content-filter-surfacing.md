<!-- capsule-v2 -->
# Content-filter finish surfacing — how does a refused response become a session error instead of silent idle?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** Which assistant finish values must be converted into persisted errors before the loop exits, and what does the user still see?

## Finish-as-error gate
**Path/Symbol:** `packages/opencode/src/session/prompt.ts` (:1295–1317, inside runLoop outcome block).
**Signature:** post-`handle.process` inspection of `handle.message.finish` when `finished && !handle.message.error`.
**Data Shape:** `finished = handle.message.finish && !["tool-calls","unknown"].includes(finish)`. `content-filter` ⇒ `SessionV1.ContentFilterError{message:"The response was blocked by the provider's content filter"}`; json_schema format with terminal finish but no captured output ⇒ `SessionV1.StructuredOutputError{retries:0}`. Both are stamped on `handle.message.error`, updated, and published to `Session.Event.Error`.

### Decisive source
```ts
// prompt.ts:1301-1308 — Anthropic stop_reason: refusal lands here
if (handle.message.finish === "content-filter") {
  handle.message.error = new SessionV1.ContentFilterError({
    message: "The response was blocked by the provider's content filter",
  }).toObject()
  yield* sessions.updateMessage(handle.message)
  yield* events.publish(Session.Event.Error, { sessionID, error: handle.message.error })
  return "break" as const
}
```

**Flow:** processor streams the response → message carries partial text parts + `finish: "content-filter"` → loop detects terminal non-tool-calls finish without existing error → converts to typed error ON THE MESSAGE (not an exception), persists, publishes, breaks. Partial streamed text REMAINS in parts — the error is additive.
**Invariant:** Without this conversion the session goes idle silently while the provider swallowed the answer ("These turns may have produced no visible output at all"). The error must live on the message record so UI/history replay shows it; throwing would lose the persisted partial output. `unknown` finishes are deliberately NOT errors (provider quirk tolerance).
**Probe:** `packages/opencode/test/session/prompt.test.ts:631` "loop surfaces content-filter finishes as session errors" — asserts `result.info.finish === "content-filter"`, stored error equals published event error (`errors` array from `events.listen`), AND `parts` arrayContaining partial "partial response" text.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "content filter finish refusal", limit: 8 });
```

## Verdict
Adopt finish→typed-error surfacing with additive partial output; adapt error taxonomy names to host schema; omit provider-specific stop_reason mapping details beyond content-filter/unknown/tool-calls handling.
