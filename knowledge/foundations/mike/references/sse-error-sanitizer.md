<!-- capsule-v2 -->
# SSE error sanitizer — how do internal errors stream to a browser without leaking internals?

**Source:** mike AGPL-3.0 `main@3ad9a5ff`; Codebase Memory `ext-mike`. **Question:** What single choke point guarantees no stack trace, provider message, or tool error text ever reaches the SSE client?

## Allowlist-by-flag error events + wholesale per-event error replacement
**Path/Symbol:** `backend/src/lib/chat/streaming.ts:125` (`ASSISTANT_ERROR_MESSAGE`), `:129` (`sanitizeAssistantEvent`), `:141` (`sanitizeAssistantSseChunk`), `:237` (`write = unsafeWrite(sanitizeAssistantSseChunk(chunk))`). Direct test: integration suites assert the safe message; unit-level behavior pinned in `src/middleware/internalErrorResponse.test.ts` for the HTTP twin.
**Signature:** `sanitizeAssistantSseChunk(chunk) -> chunk`; applied INSIDE the `write` wrapper so every emitter (tools, citations, errors) is covered by construction.
**Data Shape:** two sanitization rules — top-level `type:"error"` events pass through ONLY with `safe_to_display:true`, else their message becomes `ASSISTANT_ERROR_MESSAGE`; ANY other event carrying an `error` STRING field gets it replaced wholesale with `TOOL_ERROR_MESSAGE`.

### Decisive source
```ts
if (event.type === "error") {
    return event.safe_to_display ? event : { ...event, message: ASSISTANT_ERROR_MESSAGE };
}
if ("error" in event && typeof event.error === "string" && event.error) {
    return { ...event, error: TOOL_ERROR_MESSAGE };   // "This tool could not complete its request."
}
```

**Flow:** any code path wanting to show raw detail must EXPLICITLY construct a UserFacingError-derived event (`safe_to_display` set at :607-612 where `err instanceof UserFacingError` decides) → everything else funnels to the generic copy → non-JSON chunks and `[DONE]` pass through untouched.
**Invariant:** The default is DENY for display; opt-in is per-event. Provider/stream failures are logged server-side (`console.error`) while the client sees only the canned text. Persisted history uses the same sanitized events (`events.map(sanitizeAssistantEvent)` before both AssistantStreamError payloads and return), so replays can't leak what live streams didn't.
**Probe:** `grep -c 'safe_to_display' src/lib/chat/streaming.ts` → 3; `grep -c 'ASSISTANT_ERROR_MESSAGE' src/lib/chat/streaming.ts` → 3 (:125 def, :133 sanitizer, :608 catch).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-mike", query: "runLLMStream sanitizeAssistantEvent error streaming", limit: 10 });
```

## Verdict
Adopt deny-by-default display gating + one write-path choke point + sanitize-before-persist; adapt the allowlist flag name and canned copy to your product voice.
