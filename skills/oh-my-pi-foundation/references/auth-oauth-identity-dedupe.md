<!-- capsule-v2 -->
# OAuth identity dedupe & org scoping — when does re-login replace a stored account vs add a second row?

**Source:** oh-my-pi (see pack SKILL.md Provenance) MIT; Codebase Memory `oh-my-pi`. **Question:** How are duplicate OAuth credentials detected (JWT claim extraction), and why do Anthropic/Codex keys carry an org qualifier?

## OAuth identity dedupe & org scoping
**Path/Symbol:** `packages/ai/src/auth/sqlite-credential-store.ts:` `resolveCredentialIdentityKey` (196–199) + `resolveProviderCredentialIdentityKey` (168–194) + `extractOAuthTokenIdentifiers` (:293–341); consumer `auth-storage.ts` `#pruneDuplicateStoredCredentials` (1678–1708).
**Signature:** `resolveCredentialIdentityKey(provider: string, credential: AuthCredential): string | null` — `null` for api_key rows and identifier-less OAuth rows.
**Data Shape:** Identifiers extracted from the credential object AND by base64url-decoding JWT access/refresh payloads (`email`, `https://api.openai.com/profile`.email, `account_id|accountId|user_id|sub`, `chatgpt_account_id`) into `email:`/`account:`/`project:`/`org:` strings. Key = first of email → account → project (non-Anthropic/Codex); for anthropic/openai-codex: `<base>|org:<id>` when an org exists.

### Decisive source
```ts
if (provider === "anthropic" || provider === "openai-codex") {
	// One account email can hold several organizations/workspaces ... each with
	// its own org-scoped token and limit pools. Scope identity by org so both
	// subscriptions can be stored side by side.
	const base =
		emailIdentifier ??
		identifiers.find(identifier => identifier.startsWith("account:")) ??
		identifiers.find(identifier => identifier.startsWith("project:"));
	const orgIdentifier = identifiers.find(identifier => identifier.startsWith("org:"));
	if (base) return orgIdentifier ? `${base}|${orgIdentifier}` : base;
	// No base identity at all: the org alone still distinguishes the row.
	return orgIdentifier ?? null;
}
```

**Flow:** login/upsert/reload all funnel through identity-key matching (`matchesReplacementCredential`): same key ⇒ in-place update instead of duplicate insert. `#pruneDuplicateStoredCredentials` deletes older duplicates at reload with cause `"deduplicated duplicate credential"` and resets provider assignment state. One-way upgrade: an incoming ORG-scoped key may claim a legacy bare row (same base identity), never the reverse.
**Invariant:** Identity is per-ORG for org-scoped providers — two subscriptions on one email must coexist; matching on any single dimension (email alone) collapses them. Rows written before org capture keep bare keys and only merge among themselves. Sentinel refresh tokens (`__remote__`) never participate in matching (`#findStoredCredentialIdForUsageCredential` :3196–3202 strips them).
**Probe:** `packages/ai/test/auth-storage-email-dedupe.test.ts` — `dedupes openai-codex credentials when email matches but accountId differs` (:144); `packages/ai/test/auth-storage-org-scoped-identity.test.ts` — `stores two subscriptions of one email side by side...` (:88), `never clobbers org-scoped rows with an org-less credential` (:127), `never claims across orgs even when the stored credential shares every base identity` (:304).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "oh-my-pi", query: "resolveCredentialIdentityKey", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt JWT-claim identifier extraction + org-scoped key composition + delete-older-duplicate semantics; adapt which providers are "org-scoped" to host; omit OpenAI-specific claim URLs only if the host has no Codex analog. Porting with plain email equality silently destroys multi-subscription setups.
