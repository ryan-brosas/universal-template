<!-- capsule-v2 -->
# HTTP transport verbs — how does every provider dialect share ONE error-normalizing fetch wrapper without duplicating status/error plumbing?

**Source:** Vercel AI SDK Apache-2.0 `main@d25cae2722bfaed94c56d992c6df399a736db7a9`; Codebase Memory `ai`. **Question:** How do POST and GET requests normalize every failure mode into `APICallError` while preserving abort errors and retryability?

## postToApi / postJsonToApi / postFormDataToApi
**Path/Symbol:** `packages/provider-utils/src/post-to-api.ts:postToApi` (:77-166), `postJsonToApi` (:14-45), `postFormDataToApi` (:47-75).
**Signature:** `postToApi({url, headers?, body: {content: string|FormData|Uint8Array|Blob, values: unknown}, successfulResponseHandler: ResponseHandler<T>, failedResponseHandler: ResponseHandler<Error>, abortSignal?, fetch?}): Promise<T>`.
**Data Shape:** `body` is a PAIR — `content` is what goes on the wire, `values` is what lands in `requestBodyValues` on every error (`postJsonToApi` sets `content: JSON.stringify(body), values: body`; formData uses `Object.fromEntries(formData.entries())`). Headers default `{}` and get a UA suffix applied (`ai-sdk/provider-utils/<VERSION>` + runtime agent).

### Decisive source
```ts
const response = await fetch(url, { method: 'POST',
  headers: withUserAgentSuffix(headers, `ai-sdk/provider-utils/${VERSION}`, ...),
  body: body.content, signal: abortSignal });
const responseHeaders = extractResponseHeaders(response);
if (!response.ok) {
  let errorInformation;
  try {
    errorInformation = await failedResponseHandler({ response, url, requestBodyValues: body.values });
  } catch (error) {
    if (isAbortError(error) || APICallError.isInstance(error)) throw error;
    throw new APICallError({ message: 'Failed to process error response', cause: error,
      statusCode: response.status, url, responseHeaders, requestBodyValues: body.values });
  }
  throw errorInformation.value;            // handler RETURNS an error; wrapper THROWS it
}
try {
  return await successfulResponseHandler({ response, url, requestBodyValues: body.values });
} catch (error) {
  if (error instanceof Error && (isAbortError(error) || APICallError.isInstance(error))) throw error;
  throw new APICallError({ message: 'Failed to process successful response', cause: error, ... });
}
```
(outermost `catch` routes through `handleFetchError({error, url, requestBodyValues})`.)

**Flow:** fetch → extract headers → non-ok ⇒ failedResponseHandler produces an Error VALUE which the wrapper throws (handler failure re-wraps unless abort/APICallError) → ok ⇒ successfulResponseHandler parses (its failures wrap as `'Failed to process successful response'`) → network-level throws funnel through handleFetchError.
**Invariant:** Abort errors and already-typed APICallErrors pass through EVERY layer untouched; a throwing failed-response handler must never mask the real status code (it becomes a wrapped APICallError carrying it). The success-path parse failure is distinguishable from server errors ONLY by its message — both are APICallError.
**Probe:** `packages/provider-utils/src/get-from-api.test.ts` (shared shape): `:105+` error-handler-throws path; `post-to-api.ts` itself has NO direct unit suite at this pin (exercised via provider dialect tests — recorded caveat).

## getFromApi — same skeleton plus credential-scoping and validated redirects
**Path/Symbol:** `packages/provider-utils/src/get-from-api.ts:getFromApi` (:16-154).
**Signature:** adds `validateUrl?: boolean`, `credentialedOrigin?: string`, `trustedOrigin?: string` over the POST shape; GET has no body so `requestBodyValues: {}`.
**Data Shape:** `credentialedOrigin` = developer-configured base URL origin; headers ride ONLY to same-origin hosts. `trustedOrigin` = config-derived origin exempt from target validation (never derived from responses).

### Decisive source
```ts
// Withhold caller headers when the URL is not same-origin with the origin
// allowed to receive credentials; the user-agent suffix is still applied.
const outgoingHeaders =
  credentialedOrigin !== undefined && !isSameOrigin(url, credentialedOrigin)
    ? {}
    : headers;
const response = validateUrl
  ? await fetchWithValidatedRedirects({ url, headers: requestHeaders, abortSignal, fetch, trustedOrigin })
  : await requestFetch(url, { method: 'GET', headers: requestHeaders, signal: abortSignal });
```

**Flow:** header scoping → optional SSRF-validated redirect chain → identical ok/not-ok handler skeleton as POST.
**Invariant:** Omitting `validateUrl` behaves like `false` (no validation) for back-compat, but repo policy (comment :33-44, `contributing/secure-url-handling.md`) requires every provider call site to pass it EXPLICITLY so each trust decision is visible in source. Credential withholding triggers only when `credentialedOrigin` is SET — passing none means credentials go everywhere you address.
**Probe:** `packages/provider-utils/src/get-from-api.test.ts:31` (validates initial URL before requesting), `:248` (skips validation for hops same-origin with trustedOrigin), `:266` (validates other origins even when trustedOrigin set).

## Get live surrounding code
**Retrieve:**
```bash
echo '{"project":"ai","query":"postToApi getFromApi successfulResponseHandler failedResponseHandler","limit":5}' | codebase-memory-mcp cli search_graph
```

## Verdict
Adopt the two-handler skeleton (successfulResponseHandler/failedResponseHandler returning values/errors that the verb wrapper throws) and the abort/APICallError passthrough ladder verbatim; adapt the header pair (`content` vs `values`) to your wire format; omit the repo-specific contributing-doc policy. Caveat: post-to-api verbs lack a direct unit file — behavior is pinned via the shared-shape get-from-api suite and provider tests.
