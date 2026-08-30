<!-- capsule-v2 -->
# Fetch clone/chunked ladder — when may you `resp.clone()` to read a response body, and how do you tee json()/text() without consuming the app's stream?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** How does an instrumenting fetch wrapper capture response bodies for streaming, binary, and normal responses while leaving the application's view byte-identical?

## Chunked ⇒ no clone; else clone-once + content-type reader
**Path/Symbol:** `networkProxy/src/fetchProxy.ts:afterFetch` (:231-294), `handleResponseBody` (:296-312), `ResponseProxyHandler.get` (:30-58); abort double-notify guard (:106-128, :154-170).
**Signature:** `afterFetch(item, onResolved?): (resp: Response) => Response | Proxy`; `handleResponseBody(resp: Response, item): Promise<string | ArrayBuffer>`.
**Data Shape:** `transfer-encoding: chunked` detected by scanning response header VALUES for "chunked"; content-type drives reader choice: `application/json`→text() as json, `text/html|text/plain`→text(), anything else→arrayBuffer(); only `application/json` or `text/*` CTs get the proxy wrapper.

### Decisive source
```ts
if (isChunked) {
  // when `transfer-encoding` is chunked, the response is a stream which is under loading,
  // so the `readyState` should be 3 (Loading),
  // and the response should NOT be `clone()` which will affect stream reading.
  item.readyState = 3
} else {
  item.readyState = 4
  this.handleResponseBody(resp.clone(), item)...
}
...
return isTextLike
  ? new Proxy(resp, new ResponseProxyHandler(resp, item))
  : resp;
```

**Flow:** resolve → record status/duration/headers → chunked? mark Loading and return untouched : clone once and read the CLONE in background, then getMessage()+sendMessage → text-like CTs get a Response proxy whose get-trap tees json/text/formData (records responseType + body string, still returns the original parsed value to the app) while arrayBuffer/blob are plain bound passthroughs. Abort path: signal listener + catch share one `abortedNotified` flag so exactly ONE "Aborted" message (status 0) is sent and AbortError is rethrown.
**Invariant:** Never call `.clone()` on a streaming (chunked) response — it corrupts the app's stream. The clone is read on the recorder's copy only; the app's object must never be consumed first. Binary CTs skip the proxy entirely (nothing text-shaped to record).
**Probe:** `networkProxy/tests/fetchProxy.test.ts` — "does not clone for chunked responses" asserts `cloneSpy` not called + no sendMessage; "reads arrayBuffer for non-text content" asserts responseSize 3; abort case asserts exactly one message with status 0. Runner caveat: vitest not installed in checkout (`node_modules/.bin/vitest` absent), suite not executed this pass — assertions verified by direct read of the test source. Deterministic anchors: `grep -c chunked networkProxy/src/fetchProxy.ts` → `3`; `grep -c 'resp.clone()' networkProxy/src/fetchProxy.ts` → `1`.
**Coverage:** fetchProxy.ts + fetchProxy.test.ts `no_recorded_issue`/`metadata_match` @ gen 2026-08-25T20:08:30Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "afterFetch beforeFetch handleResponseBody ResponseProxyHandler clone chunked response body", limit: 10 });
```
(Executed at pin: top hits handleResponseBody/beforeFetch/afterFetch/ResponseProxyHandler in fetchProxy.ts plus the React Native twin.)

## Verdict
Adopt clone-only-when-not-chunked and the tee-don't-consume proxy methods. Adapt the content-type→reader table to your body budget. Omit the Response proxy for non-text CTs your product doesn't render.
