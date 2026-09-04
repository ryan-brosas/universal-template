<!-- capsule-v2 -->
# Network message sanitize order — in what order must header filtering, body obscuring, URL masking, and user sanitize run when finalizing a recorded request?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** Which sanitization step owns which surface, and why does the session-token header get written AFTER the ignore filter while the user sanitizer runs LAST with veto power?

## Finalization pipeline inside getMessage()
**Path/Symbol:** `networkProxy/src/networkMessage.ts:getMessage` (:47-89, GraphQL rewrite :69-76), `writeHeaders` (:91-106), `isHeaderIgnored` (:108-114); `networkProxy/src/sanitizers.ts:sensitiveParams` (:1-28), `obscure` (:34-43), `filterHeaders` (:45-65), `filterBody` (:67-106), `sanitizeObject`/`obscureSensitiveData` (:108-126), `tryFilterUrl` (:128-143).
**Signature:** `getMessage(): INetworkMessage | null`; `filterBody(body): string`; `tryFilterUrl(url): string`; `obscure(value: string | number)`.
**Data Shape:** 27-entry `sensitiveParams` Set (lowercased compare); obscure is length-preserving: strings → '*' per non-whitespace char (whitespace class includes \f\n\r\t\v\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff\s), numbers → same digit count of '9'.

### Decisive source
```ts
// getMessage(), in order:
const { reqHs, resHs } = this.writeHeaders()          // 1. drop ignored, then inject token
const reqBody = this.method === 'GET'
  ? JSON.stringify(sanitizeObject(this.getData))       // 2. GET data as obscured JSON
  : filterBody(this.requestData)                       //    else JSON→recur / query→params / raw
...
const messageInfo = this.sanitize({                    // 4. user hook LAST, may return null
  url: tryFilterUrl(this.url),                         // 3. fixed '******' on sensitive params
  ...
})
if (!messageInfo) return null
const isGraphql = ...url.includes("/graphql") || headers include "application/graphql-response"
if (isGraphql && body?.includes("errors")) messageInfo.status = 400 : 200
```

**Flow:** writeHeaders filters by case-insensitive list (or ALL if `ignoredHeaders === true`) and THEN calls setSessionTokenHeader so the recorder's own token always survives its own redaction → bodies triaged JSON-parse-success → recursive key-obscure → re-stringify; else `?`+`=` heuristic → URLSearchParams round-trip; else raw passthrough → URL query params replaced with literal `'******'` (URL API; unparseable URLs pass through untouched) → user sanitize may delete the whole message by returning null → GraphQL heuristic rewrites status from the body's errors key.
**Invariant:** Length-preserving masking keeps replay analytics useful without leaking values; the token-injection-after-filter ordering means an ignore-list containing your own header name does NOT break session correlation. A sanitizer returning null must suppress the send entirely — never ship the unsanitized object.
**Probe:** `networkProxy/tests/networkMessage.test.ts` pins `'******'` for a 6-char token and `'*********'` for a 9-char password, cookie dropped from both maps, `setSessionTokenHeader` called exactly once, `ignoreHeaders=true` ignores every header. Runner caveat: vitest not installed in checkout AND the suite has an upstream defect at pin — `:54 startTime: result!.startTime` evaluates inside the `expected` literal while `result` (:33) is still in TDZ, so executing it throws ReferenceError. Assertions verified by direct read only. Deterministic anchors: `grep -c 'sensitiveParams.has' networkProxy/src/sanitizers.ts` → `5`; `grep -c 'application/graphql-response' networkProxy/src/networkMessage.ts` → `1`.
**Coverage:** networkMessage.ts + sanitizers.ts + both test files `no_recorded_issue`/`metadata_match` @ gen 2026-08-25T20:08:30Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "getMessage filterHeaders filterBody obscureSensitiveData tryFilterUrl graphql sensitive headers", limit: 10 });
```
(Executed at pin: top hits also revealed near-verbatim duplicates of all four sanitizers in spot/utils/networkTrackingUtils.ts :172-258 — the ladder is copied product-wide.)

## Verdict
Adopt the pipeline ORDER (token after ignore-filter, user-sanitize last with veto) and length-preserving obscure. Adapt the sensitive-param list per product. Omit the GraphQL status rewrite unless your player renders GraphQL mutations as requests.
