<!-- capsule-v2 -->
# DoS hardening — how are per-request timeout and response-size caps enforced?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How do I bound a slow/malicious model endpoint without buffering unbounded bodies or hanging forever?

## TS fetchWithTimeout + readResponseJson
**Path/Symbol:** `typescript/src/model.ts:469-474` (`fetchWithTimeout`), `:483-506` (`readResponseJson`); defaults :228-235. Python twin: `_read_capped` `python/src/typechat/_internal/model.py:114-139` + `_ResponseTooLargeError` :39-42.
**Signature:** TS `fetchWithTimeout(url, options, timeoutMs)` sets `options.signal = AbortSignal.timeout(timeoutMs)` only when `timeoutMs > 0`; `readResponseJson(response, maxBytes): Promise<unknown>`. Py `_read_capped(response) -> bytes` with class attr `timeout_seconds = 10`, `max_response_bytes = 100*1024*1024`.
**Data Shape:** caps are opt-out via ≤0 values; the signal stays attached to the Response so BODY READING is also bounded (documented at :463-467).

### Decisive source
```ts
const result = await reader.read();
if (result.done) break;
received += result.value.byteLength;
if (received > maxBytes) {
    await reader.cancel().catch(() => { /* ignore cancellation errors */ });
    throw new Error(`REST API response exceeded the maximum allowed size of ${maxBytes} bytes`);
}
text += decoder.decode(result.value, { stream: true });
```
```py
content_length = response.headers.get("content-length")
...
if advertised is not None and advertised > max_bytes:
    raise _ResponseTooLargeError(max_bytes)
buffer = bytearray()
async for chunk in response.aiter_bytes():
    buffer.extend(chunk)
    if len(buffer) > max_bytes:
        raise _ResponseTooLargeError(max_bytes)
```
**Flow:** TS: stream-read with running byte count → over-cap ⇒ cancel reader + throw (caught by complete's try around readResponseJson → Failure "REST API response error"). Python adds a FAST-FAIL rung first: advertised Content-Length > cap raises before reading a byte; chunked bodies hit the incremental check.
**Invariant:** oversized responses are NEVER fully buffered — abort happens mid-stream; cancellation errors are swallowed so the size error propagates. Python's `_ResponseTooLargeError` is deliberately caught SEPARATELY in `complete` (:105-106) to return Failure WITHOUT retrying — a size violation is not transient. Timeout errors ARE transient (retry ladder).
**Probe:** `grep -c 'AbortSignal.timeout(timeoutMs)' typescript/src/model.ts` (=1); `grep -c 'maximum allowed size' typescript/src/model.ts` (=1) and same string in py (=1 inside _ResponseTooLargeError). Live TS pin: `model.test.mjs` :439-454 asserts signal present by default and ABSENT when timeoutMs=0; :489-510 pins reject-over-limit + accept-within-limit streaming paths; live PY: `python -m pytest tests/test_model.py -q` (4 tests incl no-content-length streamed rejection).
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"readResponseJson maxResponseBytes timeout","limit":4}'
// rank1 Function typescript/src/model.ts 483-506
```

## Verdict
Adopt both caps + the non-retryable classification of size violations; adapt mechanism per host (AbortController vs httpx stream); omit Content-Length fast-fail only if the host strips that header. Direct tests cover BOTH languages including the streamed-no-header path — strongest-tested seam in this repo.
