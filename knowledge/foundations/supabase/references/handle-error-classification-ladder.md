<!-- capsule-v2 -->
# handleError classification ladder — how does a raw API error body become a typed, field-preserving ResponseError without leaking internals to UI?

**Source:** Supabase Apache-2.0 `master@a18253f7c7d3a967bf91599c9dcf8ae704b7d686`; Codebase Memory `supabase`. **Question:** What is the exact contract that converts an unknown thrown value into either a known classified error class or a deliberately vague fallback, and which fields must survive?

## handleError + ERROR_PATTERNS + error taxonomy
**Path/Symbol:** `apps/studio/data/fetchers.ts:180-245` (`handleError`); `apps/studio/data/error-patterns.ts:19-24` (`ERROR_PATTERN_MAP`); `apps/studio/types/base.ts:102-128` (`ResponseError`); `apps/studio/types/api-errors.ts:6-36` (`ConnectionTimeoutError`, `UnknownAPIResponseError`).
**Signature:** `export const handleError = (error: unknown, options: HandleErrorOptions = {}): never`.
**Data Shape:** Input is any thrown value (typically the `{message|msg, code, requestId, retryAfter, requestPathname, metadata, formattedError}` envelope produced by the onResponse middleware). Output is always a throw of a `ResponseError` subclass carrying all recognized fields; `errorType` discriminates `'connection-timeout'` vs `'unknown'`.

### Decisive source
```ts
export const handleError = (error: unknown, options: HandleErrorOptions = {}): never => {
  if (error && typeof error === 'object') {
    if (options.alwaysCapture) Sentry.captureException(error, options.sentryContext)
    const errorMessage =
      'msg' in error && typeof error.msg === 'string'
        ? error.msg
        : 'message' in error && typeof error.message === 'string'
          ? error.message
          : undefined
    const errorCode = 'code' in error && typeof error.code === 'number' ? error.code : undefined
    // ...same strict typeof extraction for requestId/retryAfter/requestPathname/metadata/formattedError...
    if (errorMessage) {
      const matched = ERROR_PATTERNS.find(({ pattern }) => pattern.test(errorMessage))
      throw matched
        ? new matched.ErrorClass(errorMessage, errorCode, requestId, retryAfter, requestPathname, metadata, formattedError)
        : new UnknownAPIResponseError(/* same 7 args */)
    }
  }
  if (error !== null && typeof error === 'object' && 'stack' in error) console.error(error.stack)
  Sentry.captureException(error, options.sentryContext)
  // The message is intentionally vague because it might show up in the UI.
  throw new UnknownAPIResponseError(undefined)
}
```
```ts
// error-patterns.ts — Map keyed by class makes duplicate registration impossible by construction
const ERROR_PATTERN_MAP = new Map<ErrorConstructor, RegExp>([
  [ConnectionTimeoutError, /CONNECTION\s+TERMINATED\s+DUE\s+TO\s+CONNECTION\s+TIMEOUT/i],
])
export const ERROR_PATTERNS: ErrorPattern[] = Array.from(ERROR_PATTERN_MAP.entries()).map(
  ([ErrorClass, pattern]) => ({ ErrorClass, pattern })
)
```

**Flow:** any thrown value → non-object (or message-less object) → log stack, Sentry-capture, throw `UnknownAPIResponseError(undefined)` → object with a usable message → first regex match in ERROR_PATTERNS wins → construct matched class with ALL seven extracted fields → no match → UnknownAPIResponseError with same fields.
**Invariant:** `msg` beats `message` when both are strings; every optional field is extracted only under strict typeof checks (a numeric `formattedError: 42` yields undefined); classified errors remain `instanceof ResponseError` (both classes subclass it); the fallback message is intentionally undefined so ResponseError's default `'API error happened while trying to communicate with the server.'` surfaces instead of server internals.
**Probe:** `apps/studio/data/handleError.test.ts` (direct upstream test, read in full this pass): pins msg-over-message priority (:94-97), case-insensitive timeout match (:38-41), field preservation on classified AND unclassified errors (:73-92), non-string formattedError rejection (:128-131), null/non-object → UnknownAPIResponseError (:61-69). Run `vitest run handleError.test.ts` from apps/studio where node_modules exist (blocked in-lane at this pin — deterministic source-pin probes used instead).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "supabase", query: "handleError error classification", file_pattern: "apps/studio/data/*", limit: 5 });
```

## Verdict
Adopt the ladder shape verbatim: strict duck typing, msg>message precedence, regex→class registry built from a Map (duplication impossible by construction), vague-message fallback. Adapt the pattern list to your domain's known failure signatures and swap Sentry for your telemetry host; keep `alwaysCapture` semantics (capture-but-still-classify). Omit Supabase-specific patterns (only connection-timeout exists today).
