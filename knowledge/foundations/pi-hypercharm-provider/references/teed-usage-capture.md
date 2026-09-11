<!-- capsule-v2 -->
# Teed-stream usage capture — how do you read cost/usage metadata off a streaming response without disturbing the consumer?

**Source:** pi-hypercharm-provider MIT `main@4520704` (drift re-entry pass 3, was `0bdfab4`); Codebase Memory project `pi-hypercharm-provider`. **Question:** How do you extract billing/usage data (and rate-limit headers) from an SSE stream that pi-ai's SDK is already consuming, with zero polling and zero interference?

## metaFetch + readUsageFromTee
**Path/Symbol:** `index.ts:570-619` (`streamHypercharm` incl. `metaFetch`), `index.ts:507-515` (`captureUsage`), `index.ts:518-566` (`readUsageFromTee`), tee-lifetime tracking `index.ts:483-496` (`trackTeeReader`/`settleTeeReaders`).
**Signature:** `metaFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response>`; `readUsageFromTee(body: ReadableStream<Uint8Array>): Promise<void>`; `settleTeeReaders(): Promise<void>`.
**Data Shape:** Hyper extends the FINAL SSE chunk's `usage` object with `usage.cost.hypercredits` (number). Rate limits ride response headers `x-ratelimit-limit-hour|day`, `x-ratelimit-remaining-hour|day`.

### Decisive source
```ts
const [bodyForSdk, bodyForMeta] = response.body.tee();
trackTeeReader(readUsageFromTee(bodyForMeta));
return new Response(bodyForSdk, {
	headers: response.headers,
	status: response.status,
	statusText: response.statusText,
});
```
And the tee-side scanner keeps a partial-line buffer so chunks split mid-JSON never lose usage:
```ts
buffer += decoder.decode(value, { stream: true });
const lines = buffer.split("\n");
buffer = lines.pop() || "";
for (const line of lines) processLine(line);   // processLine: "data: " prefix, "[DONE]" skip, JSON.parse in try/catch
```
After EOF it also flushes a trailing non-SSE `{...}` body (non-streaming completions) via `captureUsage`.

**Flow:** per-request fetch wrapper intercepts ONLY `/chat/completions` URLs → counts `pendingRequests += 1` → captures rate-limit headers (all four finite or skipped, `captureRateLimitHeaders :492-499`) → flags HTTP 402 as out-of-credits → tees the body, hands one branch to pi-ai, scans the other for usage → at `turn_end` the extension awaits ALL in-flight tees (`settleTeeReaders`) before committing pending counters.
**Invariant:** NEVER patch `globalThis.fetch` — the interceptor is created per request inside `streamHypercharm` because concurrent main/helper requests would clobber a global patch (source comment `:566-568`). The tee reader swallows all errors ("tee may error if the main stream is aborted") and always releases its lock; a slow/erroring tee can delay commit but never corrupt the main stream. Capture lands in PENDING state variables first (`pendingRequests/pendingSpendHc/pendingSawUsage`), committed exactly once at turn_end after tees settle.
**Probe:** runtime path untested upstream (smoke suite covers status.ts only) — deterministic probe: source-read confirms `.tee()` + `new Response(bodyForSdk)` rewrap preserves headers/status verbatim; record coverage caveat.
**Coverage caveat:** index.ts verified `no_recorded_issue` by check_index_coverage.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hypercharm-provider", query: "streamHypercharm", limit: 5 });
// → pi-hypercharm-provider.streamHypercharm Function index.ts 565-614
```

## Verdict
Adopt per-request fetch interception + body tee for any provider-metadata side-channel. Adapt the URL match and header names to your API. Omit the hypercredit unit assumptions (20 hc = $1 observed).
