<!-- capsule-v2 -->
# Response handler factory — how does one factory signature serve JSON bodies, SSE streams, binary payloads, and bare-status errors without each provider re-parsing?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** What is the exact contract of a `ResponseHandler`, and how do error responses stay parseable when providers return empty, non-JSON, or schema-mismatched bodies?

## ResponseHandler type + four factories
**Path/Symbol:** `packages/provider-utils/src/response-handler.ts:ResponseHandler` (:8-16), `createJsonErrorResponseHandler` (:35-99), `createEventSourceResponseHandler` (:101-119), `createJsonResponseHandler` (:121-150), `createBinaryResponseHandler` (:152-186), `createStatusCodeErrorResponseHandler` (:187-204).
**Signature:** `type ResponseHandler<RETURN_TYPE> = (options: {url, requestBodyValues: unknown, response: Response}) => PromiseLike<{value: RETURN_TYPE; rawValue?: unknown; responseHeaders?: Record<string,string>}>`.
**Data Shape:** Handlers return `{value}` (thrown by the transport verb on the failure path) or `{value, rawValue, responseHeaders}` on success; all body reads go through `readResponseBodyAsText` → `readResponseWithSizeLimit` (2 GiB default cap).

### Decisive source
```ts
// createJsonErrorResponseHandler — three-tier degradation:
const responseBody = await readResponseBodyAsText({ response, url });
if (responseBody.trim() === '') {                     // tier 1: EMPTY body
  return { responseHeaders, value: new APICallError({ message: response.statusText,
    statusCode: response.status, responseBody, isRetryable: isRetryable?.(response), ... }) };
}
try {
  const parsedError = await parseJSON({ text: responseBody, schema: errorSchema });
  return { responseHeaders, value: new APICallError({ message: errorToMessage(parsedError),
    data: parsedError, isRetryable: isRetryable?.(response, parsedError), ... }) }; // tier 2
} catch {                                             // tier 3: non-JSON / schema mismatch
  return { responseHeaders, value: new APICallError({ message: response.statusText,
    statusCode: response.status, responseBody, isRetryable: isRetryable?.(response), ... }) };
}
```
```ts
// createJsonResponseHandler — success path THROWS instead of degrading:
const parsedResult = await safeParseJSON({ text: responseBody, schema: responseSchema });
if (!parsedResult.success) throw new APICallError({ message: 'Invalid JSON response',
  cause: parsedResult.error, statusCode: response.status, responseBody, ... });
return { responseHeaders, value: parsedResult.value, rawValue: parsedResult.rawValue };
```

**Flow:** error factories DEGRADE (empty → statusText; unparsable → statusText; parsable → provider-specific message + `data` + per-error `isRetryable(response, parsedError)`); success factories THROW on schema violation. Event-source factory throws `EmptyResponseBodyError` when `response.body == null` and otherwise returns `parseJsonEventStream({stream, schema})` as its VALUE — a stream inside the handler envelope.
**Invariant:** Error parsing is best-effort and NEVER throws out of the handler (the transport verb relies on receiving an error VALUE to throw); retryability is computed per-provider via `isRetryable(response, parsedError?)` at BOTH tiers, so a provider can mark rate-limit errors retryable while auth errors are not. Success-path validation failures carry the full raw body in `APICallError.responseBody` for debugging.
**Probe:** `packages/provider-utils/src/get-from-api.test.ts` (handler wiring); no dedicated response-handler unit file at this pin — the three-tier ladder is exercised through every provider dialect's error tests (recorded caveat).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"createJsonErrorResponseHandler createEventSourceResponseHandler safeParseJSON EmptyResponseBodyError","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the handler-factory envelope (`{value, rawValue?, responseHeaders?}`) and the degrade-never-throw error ladder with per-provider isRetryable hooks verbatim; adapt the size-limit constant to your memory budget; omit legacy tool-output conversion plumbing that lives in callers of this layer. Caveat: direct coverage rides on consumer suites; the empty-body and status-text fallbacks are the two behaviors most often missed in ports.
