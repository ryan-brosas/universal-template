<!-- capsule-v2 -->
# Review transport — direct in-process LLM completion with fresh-auth re-read and structured operation parsing

**Source:** pi-hermes-memory (MIT, `main@26f0acaa7741a81ea28eb992ab7ffcfdb7b50a0c`); Codebase Memory `pi-hermes-memory`. **Question:** How does an agent run a background LLM completion (memory review/flush/consolidation/correction) in-process — resolving the model, re-reading fresh auth each call, retrying once on auth rejection only when the key changed, parsing structured memory operations, and applying them atomically with a shrink guarantee?

## Direct review transport
**Path/Symbol:** `src/handlers/review-memory-ops.ts` — `runDirectMemoryCompletion` (415–530), `resolveReviewModel` (114–125), `resolveFreshRequestAuth` (169–180), `isAuthRejection` (141–143), `parseReviewOperations` (231–262), `applyReviewOperations` (264–403), `buildDirectReviewCompletionOptions` (92–112), `usesDirectTransport` (47–49). `src/handlers/auto-consolidate.ts:triggerConsolidation` (178–287) for the lock + heartbeat wrapper.
**Signature:** `runDirectMemoryCompletion(ctx, store, projectStore, {userPrompt, systemPrompt, config, timeoutMs?, signal?, requireAtomicShrink?, expectedTarget?}, dbManager?, projectName?, deps?) → Promise<DirectReviewResult>`.
**Data Shape:** `ReviewMemoryOperation = { action: 'add'|'replace'|'remove', target: 'memory'|'user'|'project'|'failure', content?, old_text?, category?, failure_reason? }`. `DirectReviewResult = { ok, appliedCount, fallbackReason?: 'no_model'|'no_auth'|'aborted'|'parse_error'|'provider_error'|'empty', error? }`. The LLM returns a JSON payload `{ operations: [...] }` (or "nothing to save").

### Decisive source
```ts
// resolveFreshRequestAuth (169-180): re-read auth.json per completion (key rotation visibility)
modelRegistry.authStorage?.reload(); // synchronous re-read; ignore malformed file
return modelRegistry.getApiKeyAndHeaders(model);

// runDirectMemoryCompletion (415-530): resolve model + fresh auth, then complete
const model = resolveReviewModel(ctx.model, ctx.modelRegistry, options.config);
if (!model) return { ok:false, appliedCount:0, fallbackReason:"no_model" };
const auth = await resolveFreshRequestAuth(ctx.modelRegistry, model);
if (!auth.ok || !auth.apiKey) return { ok:false, appliedCount:0, fallbackReason:"no_auth", error:... };
// timeout via AbortController; then complete(...)
try { response = await complete(model, request, buildDirectReviewCompletionOptions(...)); }
catch (err) {
  const message = err instanceof Error ? err.message : String(err);
  if (controller.signal.aborted || !isAuthRejection(message)) throw err;
  // provider rejected the key mid-flight — re-read and retry ONCE, only if key changed
  const rotated = await resolveFreshRequestAuth(ctx.modelRegistry, model);
  if (!rotated.ok || !rotated.apiKey || rotated.apiKey === requestAuth.apiKey) throw err;
  requestAuth = { apiKey: rotated.apiKey, headers: rotated.headers, env: rotated.env };
  response = await complete(model, request, buildDirectReviewCompletionOptions(...));
}
if (response.stopReason === "aborted") return { ok:false, appliedCount:0, fallbackReason:"aborted" };
const operations = parseReviewOperations(responseText(response.content));
if (operations === null) return { ok:false, appliedCount:0, fallbackReason:"parse_error" };
if (operations.length === 0) return { ok:true, appliedCount:0, fallbackReason:"empty" };
const applied = await applyReviewOperations(store, projectStore, operations, ...);

// parseReviewOperations (231-262): lenient JSON extraction (bare, fenced, or first {...})
// "nothing to save" → []; invalid → null; only valid action+target ops kept

// applyReviewOperations (264-403): requireAtomicShrink → applyMutationPlan with requireShrink:true
// (single target, atomic, must shrink); else per-op add/replace/remove with skip counting
```

**Flow:** (1) `usesDirectTransport` gates direct vs subprocess. (2) `runDirectMemoryCompletion` resolves the model (honoring `llmModelOverride`), re-reads fresh auth, and runs the completion under a timeout/abort signal. (3) On an auth-rejection mid-flight, re-reads auth and retries once — only if the key actually changed (a rotation tool may have written a new one). (4) Parses the structured operations leniently, then applies them (atomic shrink plan or per-op). (5) `triggerConsolidation` wraps the same path with a cross-process lock + heartbeat so a legitimately long consolidation never loses its lease.

**Invariant:** auth is re-read per completion so a rotated key is picked up (not frozen for the process lifetime); an auth rejection retries only when the key changed (otherwise a real auth problem falls through to the subprocess); the direct path never leaves partial atomic changes on failure; a consolidation holder beats its lease so it is never reclaimed mid-run.

**Probe:** `tests/handlers/review-memory-ops.test.ts` — `re-reads credentials before each completion so a rotated key is picked up` (:110), `retries once with the rotated key when the provider rejects the current one` (:130), `does not retry when the refreshed key is the same one the provider rejected` (:153), `classifies provider auth rejections without swallowing other failures` (:191), `parses valid JSON operations` (:216), `extracts JSON from fenced blocks` (:236), `rolls back the entire atomic plan when a later operation fails` (:290), `rejects mixed and unexpected atomic targets before mutation` (:322), `returns an actionable direct-completion error without partial atomic changes` (:529). Coverage caveat: `tests/` is excluded from the index by design, so probes are source-grounded from the on-disk test files.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-hermes-memory", query: "runDirectMemoryCompletion resolveFreshRequestAuth parseReviewOperations applyReviewOperations isAuthRejection", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the fresh-auth re-read, the auth-rejection retry-once-when-key-changed, the lenient structured-operation parsing, and the atomic-shrink application. Adapt the model resolution, the auth storage API, and the operation schema to the host. Omit the `pi -p` subprocess fallback, the consolidation lock/heartbeat, and the Pi event wiring unless a target has them.
