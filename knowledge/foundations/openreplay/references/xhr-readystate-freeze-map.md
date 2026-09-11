<!-- capsule-v2 -->
# XHR readyState freeze map — which request fields may be written at which readyState, and how does an abort keep its status?

**Source:** OpenReplay AGPL-3.0 `main@99eb60032f70906f6887195c400f173c00a08522`; Codebase Memory `openreplay`. **Question:** When recording XHR traffic through a Proxy, what is the per-readyState update contract that yields correct status/headers/duration without racing the app's own handlers?

## Constructor-trap instance proxy + listener pre-emption
**Path/Symbol:** `networkProxy/src/xhrProxy.ts:XHRProxy.create` (:296-321 construct trap), `XHRProxyHandler.constructor` (:24-53), `get("send")` token gate (:60-67), `onReadyStateChange` (:96-117), `updateItemByReadyState` (:210-292), abort/timeout senders (:119-137).
**Signature:** `updateItemByReadyState(): void`; `onReadyStateChange(): void`; constructor installs `XMLReq.onreadystatechange/onabort/ontimeout` and wraps any app assignment via `setOnReadyStateChange` (:174-183) so the handler runs BEFORE the app callback.
**Data Shape:** One `NetworkMessage` per XHR instance; `RequestState` enum UNSENT=0…DONE=4 mirrors the wire; response size probe handles string `.length`, ArrayBuffer `.byteLength`, Blob `.size`.

### Decisive source
```ts
case RequestState.DONE:
  // `XMLReq.abort()` will change `status` from 200 to 0, so use previous value in this case
  this.item.status = this.XMLReq.status || this.item.status || 0
  ...
// get("send"): inject session header only while still in OPENED
if (target.readyState === 1) target.setRequestHeader(name, value)
```

**Flow:** open() records method/url/GET-data → setRequestHeader() mirrored into item → send() injects token (only if readyState===1) + serializes body → each readyState transition updates exactly its own fields (UNSENT/OPENED: latch startTime once; HEADERS_RECEIVED: real status + parse `getAllResponseHeaders()` lines on ": " with value rejoin ": "; LOADING: size probe only) → DONE finalizes duration/statusText and, for ''/text/json responseTypes, sends via getMessage(). Text-ish bodies are copied in a `setTimeout(0)` (:104-109) after DONE so the platform has filled `response`.
**Invariant:** `abort()` zeroes `xhr.status` — the recorded status must fall back to the last non-zero seen (`status || item.status || 0`), or every aborted success records as 0/"0". Handler listeners must wrap, not replace, app handlers.
**Probe:** no dedicated upstream test file covers xhrProxy at pin (tests exist for fetchProxy/network-utils/networkMessage only) — deterministic anchors instead: `grep -c 'readyState === 1' networkProxy/src/xhrProxy.ts` → `1`; `grep -cF 'this.XMLReq.status || this.item.status || 0' networkProxy/src/xhrProxy.ts` → `1`. Recorded as a coverage caveat.
**Coverage:** xhrProxy.ts `no_recorded_issue`/`metadata_match` @ gen 2026-08-25T20:08:30Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "openreplay", query: "updateItemByReadyState onReadyStateChange onAbort onTimeout XHR ready state", limit: 10 });
```
(Executed at pin: top hits were xhrProxy.ts :96-117/:210-292 plus a React Native twin under tracker-reactnative/src/Network/xhrProxy.ts.)

## Verdict
Adopt the per-readyState field-freeze map and the abort-status fallback verbatim. Adapt the size probe to your response container types. Omit the setTimeout(0) read-delay if your runtime guarantees response availability synchronously at DONE (browsers do not).
