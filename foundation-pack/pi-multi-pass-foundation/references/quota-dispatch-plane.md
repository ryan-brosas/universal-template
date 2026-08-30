<!-- capsule-v2 -->
# Quota dispatch plane — how do you discover which accounts have a checkable provider and fan out health checks without one bad account breaking the batch?

**Source:** pi-multi-pass MIT-declared per package.json (no LICENSE file at pin; citations-only) `main@b9d9d1d7a09252a19ec79868517d49d4f07c4760`; Codebase Memory `pi-multi-pass`. **Question:** Given N accounts across several providers, how does the source decide WHICH accounts get a quota check, run them concurrently, and keep unknown/unauthenticated providers from throwing or stalling the batch?

## Registry-driven discovery -> parallel dispatch -> sorted typed results
**Path/Symbol:** `extensions/multi-sub.ts`: `collectQuotaAccounts` (1202-1236), `runQuotaChecks` (741-756), `loadQuotaResults` (758-787), `normalizeQuotaAllowedProviderNames` (1195-1200); contracts `ProviderQuotaChecker` (298-301), `QuotaAccount` (283-288).
**Signature:** `function collectQuotaAccounts(ctx: ExtensionContext): QuotaAccount[]`; `async function runQuotaChecks(accounts: QuotaAccount[], signal?: AbortSignal): Promise<QuotaCheckResult[]>`; `async function loadQuotaResults(ctx: ExtensionCommandContext, accounts: QuotaAccount[]): Promise<QuotaCheckResult[] | null>`.
**Data Shape:** QuotaAccount = {providerName, baseProvider, displayName, auth?}; ProviderQuotaChecker = {baseProvider, check(account, signal?): Promise<QuotaCheckResult>}; discovery iterates PROVIDER_QUOTA_CHECKERS and emits the base account first, then every `${provider}-${index}` subscription of that base.

### Decisive source
```ts
// discovery: checker registry drives which providers are even considered
for (const checker of PROVIDER_QUOTA_CHECKERS) {
	if (ctx.modelRegistry.authStorage.hasAuth(checker.baseProvider)) {
		pushAccount(checker.baseProvider, ...);
	}
	for (const entry of allSubs) {
		if (entry.provider !== checker.baseProvider) continue;
		pushAccount(subProviderName(entry), subDisplayName(entry));
	}
}
// pushAccount gates: exact allow-list membership + seen-dedup; baseProvider derived via getBaseProvider
// dispatch: parallel, unknown base skipped as undefined, sorted by the fixed total order
const results = await Promise.all(accounts.map(async (account) => {
	const checker = PROVIDER_QUOTA_CHECKERS.find((c) => c.baseProvider === account.baseProvider);
	if (!checker) return undefined;
	return checker.check(account, signal);
}));
return results.filter((r): r is QuotaCheckResult => Boolean(r)).sort(compareQuotaResults);
```

**Flow:** merge global+env subscriptions through the same normalize/merge plane as routing -> project `.pi/multi-pass.json` allowedSubs becomes an optional exact allow-list (trim/dedupe; empty means unrestricted; undefined means no project file) -> walk the CHECKER REGISTRY (not the account list): authenticated base account first, then each sub clone whose base matches -> allow-list filter + dedup by provider name produce QuotaAccounts carrying their auth entry -> `runQuotaChecks` fires all checks concurrently under one AbortSignal; an account whose baseProvider has no checker is dropped silently, a checker's own failure becomes a typed result (kind "error"/"missing-auth"), never a rejection -> results sorted by `compareQuotaResults` so UI and failover see the same order -> `loadQuotaResults` wraps the batch: headless contexts get the raw promise; UI contexts get an abortable loader whose cancel maps to `null`, and non-abort errors also resolve `null` after logging.
**Invariant:** the registry decides the candidate set — an account with no registered checker can never be checked, and an unauthenticated base suppresses only itself, not its subs (subs carry their own auth entries); concurrency never serializes on a slow provider (single Promise.all, shared signal); no individual check failure rejects the batch; sorting happens once, centrally, with the same comparator used everywhere else.
**Probe:** `node tests/project-aware-limits-check.mjs` (pins the discovery twin `collectQuotaProviderNames`: checker-driven enumeration plus allow-list filtering to exactly ["openai-codex"] when allowedSubs restricts; green at b9d9d1d7a092). Dispatch ordering itself is pinned transitively by `node tests/subscription-limits-check.mjs` via compareQuotaResults.
**Coverage note:** extensions/multi-sub.ts, tests/project-aware-limits-check.mjs, tests/subscription-limits-check.mjs all indexed FULL, no_recorded_issue, generation match 2026-08-24T14:18:05Z; cited ranges read directly from source at the pin and byte-matched against graph snippets.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-multi-pass", query: "collectQuotaAccounts runQuotaChecks loadQuotaResults normalizeQuotaAllowedProviderNames", limit: 10, fields: ["signature"] });
```

## Verdict
Adopt registry-driven account discovery (checkers declare which base providers are checkable), exact allow-list filtering with empty-means-unrestricted semantics, single-Promise.all concurrent dispatch with a shared abort signal, unknown-base skip, and per-account typed failure results sorted by one canonical comparator. Adapt the checker interface and auth-entry shape to your host; substitute your own transport in `check`. Omit the pi BorderedLoader TUI component — keep only the contract that cancellation maps to a null result and non-abort errors degrade to null after logging.
