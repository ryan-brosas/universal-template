<!-- capsule-v2 -->
# Retry-After + env routing — how is backoff negotiated and which provider is chosen?

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does the client honor server-negotiated backoff, and how do environment variables select OpenAI vs Azure and Chat Completions vs Responses API?

## getRetryDelayMs (TS-only seam)
**Path/Symbol:** `typescript/src/model.ts:421-430` (`getRetryDelayMs`); called :301/:408. Python has NO equivalent — fixed `asyncio.sleep(retry_pause_seconds)`.
**Signature:** `getRetryDelayMs(response: Response, defaultMs: number, maxMs: number): number` — maxMs = `retryPauseMs * retryMaxAttempts` (total-budget cap).
**Data Shape:** parses ONLY integer seconds form of `retry-after`; non-finite or negative falls through to default.

### Decisive source
```ts
const retryAfter = response.headers.get("retry-after");
if (retryAfter) {
    const seconds = parseInt(retryAfter, 10);
    if (Number.isFinite(seconds) && seconds >= 0) {
        return Math.min(seconds * 1000, maxMs);
    }
}
return defaultMs;
```
**Flow:** transient status → delay = min(Retry-After·1000, pause×maxAttempts) → sleep → retryCount++.
**Invariant:** a NEGATIVE Retry-After header must fall back to the configured pause, not produce an immediate/negative sleep — pinned by a setTimeout-interception test (`model.test.mjs` :251-273 asserts scheduledDelays===[1000] with header -1000). Upstream commit d45028c "prevent negative retry-after headers" exists precisely because this was wrong before.
**Probe:** `grep -c 'case 503' typescript/src/model.ts` (=1); live pins `model.test.mjs` :223-249 (429+503 immediate-retry paths, capturedRequests.length===2).

## createLanguageModel env routing
**Path/Symbol:** `typescript/src/model.ts:157-173`; py twin `python/src/typechat/_internal/model.py:155-191`.
**Signature:** TS `createLanguageModel(env: Record<string, string|undefined>)`; py `create_language_model(vals: dict[str, str | None])`.
**Data Shape:** precedence OPENAI_API_KEY > AZURE_OPENAI_API_KEY; OpenAI additionally requires OPENAI_MODEL (endpoint defaults to chat/completions); Azure requires only the endpoint. Missing ⇒ throw "Missing environment variable" naming the FIRST missing one. Py org var is `OPENAI_ORG`, TS is `OPENAI_ORGANIZATION` — silent divergence between ports.

### Decisive source
```ts
if ((options?.useResponsesApi ?? isResponsesApiUrl(endPoint))) {
    return createResponsesFetchLanguageModel(endPoint, headers, { model }, proxy);
}
```
with `isResponsesApiUrl(url)` = `new URL(url).pathname.endsWith("/responses")`, falling back to pre-query split for relative URLs (:453-460). Responses request body uses `input` instead of `messages`; response text extracted from `output[n].content[m]` where item type==="message" AND content item type==="output_text" (:396-403).
**Invariant:** URL-shape auto-detection can be FORCED either way via `useResponsesApi` (tested against a /chat/completions URL with flag true). The two API variants share ONE retry/timeout/size stack — only body key and response unwrapping differ.
**Probe:** `grep -c 'endsWith("/responses")' typescript/src/model.ts` (=2: helper + doc reference is in comments — actual code sites are helper + none other); live pins `model.test.mjs` :201-221 (auto-detect + force), :346-403 (env routing incl both-keys-missing throw).
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"getRetryDelayMs retry transient 429","limit":4}'
// rank1 Function typescript/src/model.ts 421-430
```

## Verdict
Adopt Retry-After clamping with the negative-header fallback and the env-precedence table; adapt org-var name per port consciously; omit the Responses-API variant if targeting only legacy endpoints but keep the shared-stack structure. Direct tests cover every rung at this pin.
