<!-- capsule-v2 -->
# Compaction failure UX contract — which errors surface to the user immediately, which stay silent, and why does the abort path need exact-string matching?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you classify compaction failures for notification, retry, and telemetry without crying wolf on auto-compact?

## compact-failure-ux
**Path/Symbol:** `src/services/compact/compact.ts` (error constants :225-227/:293-297, `addErrorNotificationIfNeeded` :1108-1123, catch blocks :749-756 vs :1097-1099, streaming-retry :1250-1389).
**Signature:** `addErrorNotificationIfNeeded(error, context)` — suppresses notifications for `API Error: Request was aborted.` and `Not enough messages to compact.` (EXACT-match via `hasExactErrorMessage`, not substring).
**Data Shape:** four user-facing strings: NOT_ENOUGH_MESSAGES (:225), PROMPT_TOO_LONG (:293, esc-twice guidance), USER_ABORT (:295), INCOMPLETE_RESPONSE (:296, network framing + "try again").

### Decisive source
```ts
} catch (error) {
  // Only show the error notification for manual /compact.
  // Auto-compact failures are retried on the next turn and the
  // notification is confusing when compaction eventually succeeds.
  if (!isAutoCompact) {
    addErrorNotificationIfNeeded(error, context)
  }
  throw error
}
```
and the retry gate:
```ts
const retryEnabled = getFeatureValue_CACHED_MAY_BE_STALE(
  'tengu_compact_streaming_retry',
  false,
)
const maxAttempts = retryEnabled ? MAX_COMPACT_STREAMING_RETRIES : 1
```

**Flow:** full-compact failures notify ONLY for manual triggers (auto-compact retries next turn silently — a transient failure shouldn't alarm when the retry will succeed); partial compact always notifies. Telemetry distinguishes reasons (`prompt_too_long` / `no_summary` / `api_error` / `no_streaming_response`) with preCompactTokenCount attached to every event. The streaming path's only retryable failure is "no assistant message at all" — a response that STARTED but produced garbage still returns and gets classified upstream.
**Invariant:** user-abort must be recognized EXACTLY (`hasExactErrorMessage`) because the abort text is also what query() yields as a synthetic assistant message — substring matching would misclassify legitimate summaries containing similar words; notification suppression is a trigger-kind decision (manual vs auto), not an error-kind one; every throw re-raised after logging so callers (query loop) keep their own recovery ladder.
**Probe:** no upstream test. Deterministic pins: `grep -n "Only show the error notification" src/services/compact/compact.ts` → :750; `grep -n "hasExactErrorMessage" src/services/compact/compact.ts` → :1113-1114.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "ERROR_MESSAGE_PROMPT_TOO_LONG addErrorNotificationIfNeeded", limit: 10 });
```

## Verdict
Adopt manual-vs-auto notification gating and exact-string abort classification. Adapt message copy. Coverage caveat: no unit tests upstream.
