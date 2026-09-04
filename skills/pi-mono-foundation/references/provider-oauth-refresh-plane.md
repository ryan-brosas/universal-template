<!-- capsule-v2 -->
# provider-oauth-refresh-plane — How do I structure provider OAuth so concurrent requests never double-refresh a rotated token?

**Source:** pi-mono (MIT) `main@80e62761f7251a104f1b21d9c73920c720f0ec00`; Codebase Memory `pi-mono`. **Question:** Where do login, refresh, and request-auth derivation live, and which locking discipline makes token rotation safe under concurrency?

## Credential contract + locked refresh
**Path/Symbol:** `packages/ai/src/auth/types.ts` whole 240L (`CredentialStore` :65-94, `OAuthAuth` :206-230, `ApiKeyAuth` :170-199, `ModelAuth` :7-11, `AuthInteraction`/`AuthPrompt` :125-164); reference flows `packages/ai/src/auth/oauth/anthropic.ts` whole 364L; store `packages/ai/src/auth/credential-store.ts` `InMemoryCredentialStore` :9-67; wiring `packages/ai/src/providers/anthropic.ts` whole 59L; bundling `packages/ai/src/bun-oauth.ts` 21L.
**Signature:** `interface CredentialStore { read(providerId): Promise<Credential|undefined>; list(): Promise<readonly CredentialInfo[]>; modify(providerId, fn: (current) => Promise<Credential|undefined>): Promise<Credential|undefined>; delete(providerId): Promise<void> }`; `interface OAuthAuth { name; isSubscription?; loginLabel?; login(interaction): Promise<OAuthCredential>; refresh(credential, signal): Promise<OAuthCredential>; toAuth(credential): Promise<ModelAuth> }`.
**Data Shape:** `Credential = ApiKeyCredential{type:"api_key", key?, env?} | OAuthCredential{type:"oauth", refresh, access, expires}`; `expires = Date.now() + expires_in*1000 − 5*60*1000` (5-minute safety skew); one type-tagged credential per provider id.

### Decisive source
```ts
/**
 * Serialized write — the only write path. ... Mutual exclusion per provider id,
 * cross-process too where the backing store supports it (e.g. a file lock).
 */
modify(providerId: string, fn: (current: Credential | undefined) => Promise<Credential | undefined>, options?): Promise<Credential | undefined>;
// types.ts header comment: "Models.getAuth() runs OAuth refresh inside
// modify so concurrent requests cannot double-refresh a rotated token."
```

**Flow:** Login: `login(interaction)` produces a credential the app persists via `modify(provider.id, async () => credential)`. Request time: `Models.getAuth(providerId)` reads inside `modify`; when the OAuth credential is inside the refresh window it calls `oauth.refresh(credential, signal)` UNDER THE LOCK and stores the result, then derives wire auth with `toAuth(credential)` — side-effect-free: anthropic/openai-codex/xai return `{apiKey: access}`; github-copilot additionally derives a per-credential baseUrl (token `proxy-ep` claim → enterprise domain → `https://api.individual.githubcopilot.com`); openrouter's refresh returns the SAME permanent credential. Api-key providers resolve through `ApiKeyAuth.resolve` merging per-field credential-over-env (stored key → `ANTHROPIC_AUTH_TOKEN` env as Bearer headers → oauth/api-key envs). Anthropic login shows the flow shape: PKCE + local http callback server on 127.0.0.1:53692 racing a manual paste prompt — whichever resolves first cancels the other via per-prompt AbortSignal; state (=verifier) mismatch throws; callback server closed in finally. Provider entries register `auth:{apiKey, oauth: lazyOAuth({load})}` so flow modules load lazily; `bun-oauth.ts` swaps in statically bundled loaders for the standalone binary.
**Invariant:** `modify` is the ONLY write path and must serialize read-modify-write per provider id — refresh decisions based on a credential read outside the lock can double-refresh and invalidate rotated refresh tokens. `refresh` may throw (invalid_grant); `toAuth` must not touch network. Storage failures surface as `ModelsError` code "auth"; best-effort stores that keep an in-memory view are valid implementations.
**Probe:** `packages/ai/test/oauth-auth.test.ts` — pins subscription flags (openrouter NOT subscription), toAuth derivations incl. copilot baseUrl ladder, anthropic refresh against stubbed fetch returning typed credential, and `Models.getAuth` resolving stored credentials via the lazy load chain with `source:"OAuth"`. Coverage caveat: BLOCKED at import in this checkout (providers → gitignored generated catalog data/github-copilot.json; runner exists, fixture needs network); assertions pinned by whole-file direct reads.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-mono", query: "oauth credential refresh toAuth credential store modify lock", limit: 10, fields: ["signature", "name", "file"] });
```
Live result at pin: `InMemoryCredentialStore.modify` #1 (-43.78) with its enqueue/read/list/delete cluster top-10 — the lock path itself is the retrieval anchor.

## Verdict
Adopt the three-surface split (interactive `login`, locked `refresh`, side-effect-free `toAuth`) and the modify-only-write-path store; run getAuth-time refresh inside that lock. Adapt credential shapes to your storage but keep one type-tagged credential per provider and the 5-minute expiry skew. Omit pi's specific PKCE/callback-port mechanics only if your host has no CLI story — otherwise copy the manual-paste race pattern verbatim; it is what makes headless logins possible.
