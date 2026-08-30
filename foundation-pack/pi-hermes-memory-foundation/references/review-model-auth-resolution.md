<!-- capsule-v2 -->
# Review auth resolution — public-registry resolve + rotate-on-rejection retry (authStorage.reload() rewrite, #139 contract corrected @71beae8a)

**Source:** pi-hermes-memory (MIT, `main@71beae8a`); Codebase Memory `pi-hermes-memory`. **Question:** A headless completion path shares credentials with an interactive host — how do you resolve the API key without reaching into host internals, and when may you retry after a provider rejects the key?

## resolveRequestAuth / isAuthRejection
**Path/Symbol:** `src/handlers/review-memory-ops.ts` — `resolveRequestAuth` (:160–165), `isAuthRejection` (:141–143), `AUTH_REJECTION_PATTERN` (:131–138), type `ResolvedRequestAuth` (:147–153), retry loop in `runDirectMemoryCompletion` (:415–472). The old symbol `resolveFreshRequestAuth` NO LONGER EXISTS (grep over src/ + tests/ = zero hits).
**Signature:** `resolveRequestAuth(modelRegistry: ReviewModelRegistry, model: Model<Api>) → Promise<ResolvedRequestAuth>`; `isAuthRejection(message: string) → boolean`.
**Data Shape:** `ResolvedRequestAuth = { ok: true; apiKey?; headers?; env? } | { ok: false; error }` — mirrors the SDK's shape with a structural check against the real registry at the call site so drift is a build error.

### Decisive source
```ts
/**
 * Resolve request auth through the public ModelRegistry API. Resolve it again
 * after an auth rejection so Pi can supply refreshed credentials when its
 * registry supports that, without reaching into version-sensitive internals.
 */
export async function resolveRequestAuth(modelRegistry, model) {
  return modelRegistry.getApiKeyAndHeaders(model);
}
```
```ts
// :451-463 — the rejection-driven rotation retry:
if (controller.signal.aborted || !isAuthRejection(message)) throw err;
const rotated = await resolveRequestAuth(ctx.modelRegistry, model);
// retry ONLY if Pi now returns a DIFFERENT key than the one it rejected:
if (!rotated.ok || !rotated.apiKey || rotated.apiKey === requestAuth.apiKey) throw err;
requestAuth = { apiKey: rotated.apiKey, headers: rotated.headers, env: rotated.env };
```

**Flow:** completion attempt → on error, classify with `AUTH_REJECTION_PATTERN` (`(401|403)` word-bounded, unauthorized/forbidden, `invalid[\s_-]*api[\s_-]*key`, authentication failed/error, token/key/credential invalid|expired|revoked forms) → non-auth errors rethrow untouched → re-resolve through the registry ONCE → retry only if the key actually changed; otherwise surface as `provider_error` and let the subprocess fallback handle it.
**Invariant:** never reach into version-sensitive host internals for credentials — the whole point of this rewrite was that `modelRegistry.authStorage?.reload()` (the previous mechanism, documented here through pass 3) reached into an AuthStorage field that Pi does not guarantee; the public `getApiKeyAndHeaders` API is the stable surface. An unchanged key after rejection means a REAL auth problem, not a rotation race — exactly one retry, keyed by inequality. Abort always wins (`controller.signal.aborted` short-circuits before classification).
**Probe:** `npx tsx --test tests/handlers/review-memory-ops.test.ts` — "resolves credentials through the public registry API" (:102, asserts `registry.authCalls === 1` and the exact key used), "re-resolves credentials after a provider auth rejection" (:121, usedKeys `["revoked-key", "rotated-key"]`), "does not retry when the refreshed key is the same one the provider rejected" (:142, `usedKeys.length === 1`), "classifies provider auth rejections without swallowing other failures" (:161, 7 positive + 4 negative messages). GREEN under `npx tsx --test`.
**Retrieve:** `search_graph({ project: "pi-hermes-memory", query: "resolveRequestAuth getApiKeyAndHeaders isAuthRejection", limit: 5 })`

## Verdict
Adopt the public-API-only credential resolution and the reject-then-rotate-once ladder with strict key-inequality gating. Adapt the registry interface names to the host. OMIT any port of the old `authStorage.reload()` approach — it is gone upstream and depends on private fields. Model-override selection (`resolveReviewModel` three-tier exact-match-or-refuse) is unchanged and still owned by this module. Pair with `review-transport.md`.
