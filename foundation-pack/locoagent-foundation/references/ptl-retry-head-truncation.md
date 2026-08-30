<!-- capsule-v2 -->
# PTL retry head-truncation — when the COMPACTION REQUEST ITSELF hits prompt-too-long, how do you shrink the input without stalling or producing an assistant-first transcript?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** What is the safe algorithm for iteratively dropping oldest context under an API length error?

## ptl-retry-head-truncation
**Path/Symbol:** `src/services/compact/compact.ts` (`truncateHeadForPTLRetry` :243-291, `MAX_PTL_RETRIES` :227, `PTL_RETRY_MARKER` :228; driver loops :450-491 and :862-899).
**Signature:** `truncateHeadForPTLRetry(messages, ptlResponse): Message[] | null` — null = cannot shrink further (give up).
**Data Shape:** groups from `groupMessagesByApiRound` (group 0 = preamble, later groups start with an assistant message); token gap parsed from the error response (`getPromptTooLongTokenGap`), possibly undefined.

### Decisive source
```ts
// Strip our own synthetic marker from a previous retry before grouping.
// Otherwise it becomes its own group 0 and the 20% fallback stalls
// (drops only the marker, re-adds it, zero progress on retry 2+).
const input =
  messages[0]?.type === 'user' &&
  messages[0].isMeta &&
  messages[0].message.content === PTL_RETRY_MARKER
    ? messages.slice(1)
    : messages

const groups = groupMessagesByApiRound(input)
if (groups.length < 2) return null
...
} else {
  dropCount = Math.max(1, Math.floor(groups.length * 0.2))
}

// Keep at least one group so there's something to summarize.
dropCount = Math.min(dropCount, groups.length - 1)
```
```ts
// Dropping group 0 leaves an assistant-first sequence which the API rejects (first message must be
// role=user). Prepend a synthetic user marker — ensureToolResultPairing
// already handles any orphaned tool_results this creates.
if (sliced[0]?.type === 'assistant') {
  return [
    createUserMessage({ content: PTL_RETRY_MARKER, isMeta: true }),
    ...sliced,
  ]
}
```

**Flow:** compact request returns PROMPT_TOO_LONG text → caller increments attempt (cap 3) → drop oldest whole API-round groups until cumulative rough-token estimate covers the parsed gap (fallback: drop 20% of groups when gap unparseable — some Vertex/Bedrock formats) → retry; on final failure surface ERROR_MESSAGE_PROMPT_TOO_LONG to the user instead of leaving them stuck.
**Invariant:** (1) strip the PREVIOUS retry's synthetic marker first or the loop reaches a fixed point (drops only the marker, re-adds it, forever); (2) never drop ALL groups — one must remain to summarize; (3) an assistant-first slice needs a synthetic meta user marker prepended or the API rejects role order; (4) the truncated set must thread through BOTH code paths — the `messages` param AND `retryCacheSafeParams.forkContextMessages`, because the forked-agent path reads the latter, not the former.
**Probe:** no upstream test (tests/=shell scripts). Deterministic pins: `grep -n "zero progress on retry 2" src/services/compact/compact.ts` → :248-249; `grep -n "earlier conversation truncated for compaction retry" src/services/compact/compact.ts` → :228/:253/:286; `grep -n "forkContextMessages: truncated" src/services/compact/compact.ts` → :489/:897.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "truncateHeadForPTLRetry groupMessagesByApiRound", limit: 10 });
```

## Verdict
Adopt the group-granular drop loop with marker-strip, keep-one-group clamp, and synthetic-user prepend. Adapt grouping/token estimation to your stack. Omit vendor-specific gap parsing details. Coverage caveat: no unit tests upstream.
