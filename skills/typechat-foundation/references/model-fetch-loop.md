<!-- capsule-v2 -->
# Chat Completions fetch loop — retry, timeout, and response-shape failure ladder

**Source:** TypeChat MIT `main@83caa1242d9a9a707a4a66bfbc5fe6174cbcb8dc`; Codebase Memory `typechat`. **Question:** How does the model client classify failures, what is retryable, and how do timeout/size caps compose with the retry budget?

## createFetchLanguageModel.complete
**Path/Symbol:** `typescript/src/model.ts:240-305` (`createFetchLanguageModel`); Python twin `python/src/typechat/_internal/model.py:70-112` (`HttpxLanguageModel.complete`).
**Signature:** TS `async complete(prompt: string | PromptSection[]): Promise<Result<string>>`; knobs on the returned object: `retryMaxAttempts?` (default 3), `retryPauseMs?` (default 1000), `timeoutMs?` (default 600000), `maxResponseBytes?` (default 100×1024×1024).
**Data Shape:** body = `{...defaultParams, messages, temperature: 0, n: 1}` — temperature ZERO is a hard invariant (translation must be deterministic for repair to converge). String prompt → single user section (:255; py :76-77).

### Decisive source
```ts
} catch (e) {
    if (retryCount >= retryMaxAttempts) {
        return error(`REST API fetch error: ${getErrorMessage(e)}`);
    }
    await sleep(retryPauseMs);
    retryCount++;
    continue;
}
...
if (!isTransientHttpError(response.status) || retryCount >= retryMaxAttempts) {
    return error(`REST API error ${response.status}: ${response.statusText}`);
}
await sleep(getRetryDelayMs(response, retryPauseMs, retryPauseMs * retryMaxAttempts));
```
**Flow:** fetch → (transport throw | non-OK status | OK) → transient set {429,500,502,503,504} (TS :435-445; py `_TRANSIENT_ERROR_CODES` :31-37) retries with pause → Retry-After header honored when present (see retry-after capsule) → OK path reads capped JSON and requires `choices[0].message.content` to be a **string**, else "REST API unexpected response format" Failure.
**Invariant:** every terminal outcome is a Result, never a throw — a malformed 200 body is a recoverable Failure, NOT an exception (regression-tested: DoS-class TypeError on missing choices). The retry counter caps BOTH transport throws and HTTP statuses from ONE shared budget. Python counts a failed attempt then sleeps unconditionally (`retry_pause_seconds`, default 1.0s float) and has NO Retry-After parsing.
**Probe:** `grep -c 'case 429' typescript/src/model.ts` (=1 inside isTransientHttpError); `grep -c 'unexpected response format' typescript/src/model.ts` (=3 sites incl Responses variant); live: `typescript/tests/model.test.mjs` lines 161-199 pin all five malformed-body shapes returning success:false.
**Retrieve:**
```ts
// CLI: codebase-memory-mcp cli search_graph '{"project":"typechat","query":"isTransientHttpError REST API error retry","limit":5}'
```

## Verdict
Adopt the failure taxonomy (transient-retry vs shape-error vs transport-error) and temperature:0; adapt knob names/units per host (py uses seconds not ms); omit proxy plumbing if the host has its own egress layer. Direct tests cover both languages at this exact pin (`model.test.mjs` 512L, `test_model.py` 83L).
