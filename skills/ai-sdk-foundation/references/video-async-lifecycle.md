<!-- capsule-v2 -->
# Async video lifecycle — how does fire-and-forget generation stay idempotent and resumable across processes?

**Source:** Vercel AI SDK Apache-2.0 `main@9d9a73f1551f...`; Codebase Memory `ai`. **Question:** `experimental_startVideo` returns immediately with an opaque operation — what must a porter replicate so the operation survives process death, retries, and webhook/polling completion?

## Start/status split with billable-call idempotency
**Path/Symbol:** `packages/ai/src/generate-video/start-video.ts:experimental_startVideo` (:90–214), `get-video-status.ts:experimental_getVideoStatus` (:38–66).
**Signature:** `startVideo({model,prompt,n,...,headers,webhookUrl}) => {operation: JSONValue, warnings, providerMetadata?, response}`; `getVideoStatus(model, {operation, headers, ...})` — ONE check, no polling loop (poll on your own schedule or use webhooks).
**Data Shape:** `operation` is JSON-serializable and opaque — persist it; providerMetadata carries the provider job id (gateway `providerMetadata.gateway.asyncJob.jobId`) and webhook signing secret when used.

### Decisive source
```ts
if (model.doStart == null) throw new Error(
  `Video model ${model.modelId} does not implement doStart. Use generateVideo for models without an asynchronous start/status flow.`);
// A start yields one operation covering all n videos: refuse to silently
// exceed a known per-call limit instead of splitting into several starts.
const knownMaxVideosPerCall = maxVideosPerCall ?? (typeof model.maxVideosPerCall === 'function'
  ? await model.maxVideosPerCall({modelId}) : model.maxVideosPerCall);
if (knownMaxVideosPerCall != null && n > knownMaxVideosPerCall) throw new Error(...);
// `doStart` is billable: mint one idempotency token per logical start,
// OUTSIDE the retry closure; a caller-supplied key wins.
const callerIdempotencyKey = Object.entries(headers ?? {}).find(
  ([k,v]) => k.toLowerCase() === 'idempotency-key' && v !== undefined);
headers: { ...withUserAgentSuffix(headers ?? {}, `ai/${VERSION}`),
  ...(callerIdempotencyKey ? {} : {'idempotency-key': `aisdk_vid_${generateId()}`}) },
const startResult = await retry(() => model.doStart!(callOptions));
```

**Flow:** resolve model → demand `doStart` → validate n integer ≥1 → enforce per-call cap by THROWING (never auto-split) → normalize inputs → prepareRetries → idempotency ladder → retry(doStart) → return `{operation,…}` immediately. Status side demands `doStatus`, wraps UA header, single retry(doStatus) returning `{status:'pending'|'completed'|'error'}`.
**Invariant:** The idempotency token is minted ONCE per logical start OUTSIDE the retry loop (retrying inside would re-mint and double-bill); caller-supplied `idempotency-key` always wins via case-insensitive scan.
**Probe:** deterministic probes: `grep -cF aisdk_vid_ packages/ai/src/generate-video/start-video.ts` → `1`; `grep -cF "timeoutMs ?? 600_000" packages/ai/src/generate-video/generate-video.ts` → `1`. Direct tests: `start-video.test.ts` (313 lines: doStart guard, n validation, per-call cap, idempotency-key precedence).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ai", query: "experimental_startVideo doStart idempotency", limit: 10, fields: ["signature","name","file"] });
// verified live @9d9a73f: rank#1 experimental_startVideo :90-214
```

## Verdict
Adopt the start/status protocol shape, outside-retry idempotency minting, and throw-don't-split cap enforcement; adapt the `aisdk_vid_` prefix and providerMetadata paths; omit gateway-specific job metadata unless porting the gateway video model too.
