<!-- capsule-v2 -->
# acp-config-option-plane — how do you expose mutable provider/model/mode settings over a protocol session without breaking an in-flight conversation?

**Source:** Cline Apache-2.0 `main@4f836ae7d0ed29ece7ef4a2a478deb470fdd056e`; Codebase Memory `cline`. **Question:** What must a config-option switch validate, tear down, re-resolve, and re-broadcast — and in what order?

## Env-pinned provider is immutable; switch tears down then re-resolves the model against the NEW catalog; single-flight refresh manager; every success rebuilds and broadcasts ALL options
**Path/Symbol:** `apps/cli/src/acp/acpAgent.ts` (`setSessionConfigOption` :452-571, `resolveDefaultModelId` :762-776, `toAcpPromptError` :841-852, `mapFinishReason` :941-955) + `apps/cli/src/acp/organizations.ts` (`oauthTokenManager` singleton :44-46, `persistActiveOrganization` :120-146) + `apps/cli/src/acp/auto-approve.ts` (`parseAutoApproveValue` :22-29).
**Signature:** `setSessionConfigOption(params: SetSessionConfigOptionRequest): Promise<SetSessionConfigOptionResponse>` — switch over configId: provider | organization | model | mode | auto_approve.
**Data Shape:** Options are typed `SessionConfigOption` (select/boolean) rebuilt wholesale after EVERY successful branch; org option appended only when `usesClineAccount(providerId)` (cline | cline-pass).

### Decisive source
```ts
case "provider": {
	if (process.env.CLINE_PROVIDER) {
		throw RequestError.invalidParams(undefined,
			"Cannot change provider: CLINE_PROVIDER environment variable is set");
	}
	if (!isAcpAuthMethodId(value)) {
		throw RequestError.invalidParams(undefined, `Unknown provider: ${value}`);
	}
	session.currentProviderId = value;
	// Tear down the old session manager so ensureSessionManager()
	// creates a fresh one with the new provider on the next prompt().
	await this.teardownSessionManager(session);
	// Re-resolve the model against the new provider's catalog: keep the
	// current one when it's offered there too, otherwise fall back to the
	// provider's declared default rather than whichever model happens to
	// be listed first (for cline-pass that is an unrelated free model).
	...
}
// resolveDefaultModelId rungs: current-if-offered → provider defaultModelId → modelIds[0] ?? ""
// organizations.ts: the module-singleton RuntimeOAuthTokenManager keeps refreshes
// single-flight; the refresh token is single-use, so parallel refreshes would
// invalidate each other.
```

**Flow:** provider switch ⇒ env-pin veto ⇒ closed-vocabulary validation ⇒ teardownSessionManager (preserving messages) ⇒ re-resolve model against the NEW provider catalog (keep-if-offered → declared defaultModelId → first-listed) ⇒ org switch runs server-side first, then best-effort persistActiveOrganization (`{setLastUsed:false}`) with fail-soft catches everywhere ⇒ model/mode update in place (mode validates plan|act) ⇒ auto-approve parses boolean OR legacy string forms, anything else ⇒ undefined ⇒ invalidParams (fail-closed; 6-case suite pins "yes"/1/null/undefined) ⇒ EVERY successful branch rebuilds ALL config options (+org when applicable) and broadcasts config_option_update. Error mapping for prompt turns: toAcpPromptError special-cases the ClinePass org-subscription message, then isLikelyAuthError (type AND name/message checks — instanceof fails across the event boundary) ⇒ RequestError.authRequired (-32000) so clients offer re-auth; else internalError. mapFinishReason: completed→end_turn, aborted→cancelled, max_iterations→max_turn_requests, mistake_limit→end_turn (deliberate downgrade), default→end_turn.
**Invariant:** An env-pinned provider can never be switched at runtime; a provider switch never leaves the model pointing at an id the new catalog does not offer; OAuth refreshes are single-flight; every accepted config change leaves the client with a full, current option set; auth failures surface as auth_required, not generic errors.
**Probe:** `grep -cF 'CLINE_PROVIDER environment variable is set' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'oauthTokenManager ??= new RuntimeOAuthTokenManager' apps/cli/src/acp/organizations.ts` → 1; `grep -cF 'setLastUsed: false' apps/cli/src/acp/organizations.ts` → 1; `grep -cF 'value === "true" ? true : value === "false" ? false : undefined' apps/cli/src/acp/auto-approve.ts` → 1; `grep -cF 'sendConfigOptionUpdate(this.conn, params.sessionId, configOptions)' apps/cli/src/acp/acpAgent.ts` → 1; `grep -cF 'mistake_limit' apps/cli/src/acp/acpAgent.ts` → 1. Direct suites: auto-approve.test.ts (6 cases) + organizations.test.ts (2 cases) read whole; acpAgent.ts has NO dedicated suite (coverage caveat).

## Get live surrounding code
**Retrieve (canonical call — NOT executed this session: Codebase Memory MCP transport unavailable; recorded for a connected session):**
```ts
await mcp.codebase_memory.search_graph({ project: "cline", query: "setSessionConfigOption resolveDefaultModelId RuntimeOAuthTokenManager config_option_update", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt env-pin immutability, teardown-then-re-resolve ordering against the new catalog, declared-default-over-first-listed model fallback, single-flight token refresh, fail-closed value parsing, and rebuild-and-broadcast-all after every accepted change. Adapt the config vocabulary and provider catalog source. Omit Cline's organization persistence details. Coverage: sources+tests read whole at pin; MCP coverage check not runnable this session — recorded caveat.
