<!-- capsule-v2 -->
# Auth resolution cascade — which credential source wins when runtime flag, config pin, OAuth row, login key, env var and stored key all exist?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** What is the exact precedence ladder of `getApiKey`, and why do env vars beat stored api_keys but lose to OAuth?

## Auth resolution cascade
**Path/Symbol:** `packages/ai/src/auth-storage.ts:` `AuthStorage.getApiKey` (5594–5648) + `peekApiKey` (5534–5581) + `describeCredentialSource` (6840–6885).
**Signature:** `getApiKey(provider: string, sessionId?: string, options?: AuthApiKeyOptions): Promise<string | undefined>`.
**Data Shape:** Inputs keyed by provider string; returns bearer bytes only. The seven legs are: `#runtimeOverrides` map → `#configOverrides` map → OAuth selection (`#resolveOAuthSelection`) → login-stored api_key (`source === "login"`) → `getEnvApiKey(provider)` → non-login stored api_key → `#fallbackResolver`.

### Decisive source
```ts
async getApiKey(provider: string, sessionId?: string, options?: AuthApiKeyOptions): Promise<string | undefined> {
	// Runtime override takes highest priority
	const runtimeKey = this.#runtimeOverrides.get(provider);
	if (runtimeKey) {
		return runtimeKey;
	}
	const configKey = this.#configOverrides.get(provider);
	if (configKey) {
		return configKey;
	}
	const oauthResolved = await this.#resolveOAuthSelection(provider, sessionId, options);
	if (oauthResolved) {
		return oauthResolved.apiKey;
	}
	const loginApiKeySelection = await this.#selectApiKeyCredential(
		provider,
		sessionId,
		options,
		credential => credential.source === "login",
	);
	if (loginApiKeySelection) {
		this.#recordSessionCredential(provider, sessionId, "api_key", loginApiKeySelection.index);
		return this.#configValueResolver(loginApiKeySelection.credential.key);
	}
	if (sessionId) this.#sessionLastCredential.get(provider)?.delete(sessionId);
	const envKey = getEnvApiKey(provider);
	if (envKey) {
		return envKey;
	}
	return this.#fallbackResolver?.(provider) ?? undefined;
}
```

**Flow:** Each leg either returns bytes or falls through. Two side effects are load-bearing: recording the session sticky on the leg that won (so later resolves reuse it), and DELETING the stale OAuth sticky when resolution falls past OAuth to env/api_key — otherwise `#resolveActiveOAuthCredential` keeps injecting `account_uuid` headers for traffic that env-authenticated.
**Invariant:** A deliberate credential (runtime/config/OAuth/login) always beats ambient ones (env/stored/fallback); a stored static api_key is LAST resort because it may be a stale broker-migrated copy (`peekApiKey` :5545 comment). Config override exists specifically so a key pinned for an auth-gateway baseUrl isn't shadowed by the upstream OAuth token the proxy would reject (:5601–5605).
**Probe:** `packages/ai/test/auth-storage-config-override.test.ts` — `setConfigApiKey beats OAuth access token for getApiKey` (:47), `runtime override (--api-key) still beats setConfigApiKey` (:58), `setConfigApiKey suppresses OAuth account_uuid attribution` (:96).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "AuthStorage getApiKey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the seven-leg order and the two side effects (sticky record on win, sticky clear past OAuth); adapt leg names to host vocabulary; omit the specific provider quirks (`xai-oauth` dedicated-env special case lives in `hasAuth`/`#hasDedicatedEnvAuth`, not in this ladder).
