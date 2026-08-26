<!-- capsule-v2 -->
# Codex auth — resolve OAuth credentials registry-first with auth-file fallback, expiry check, and JWT account-id extraction

**Source:** pi-better-openai (MIT, `main@86814e9047996abba08e4c907e23286329196fe0`); Codebase Memory `pi-better-openai`. **Question:** How does an extension obtain an OpenAI Codex OAuth `accessToken` + `accountId` for authenticated API calls, preferring a live model-registry lookup and falling back to a local auth file, while honoring abort signals and rejecting expired tokens?

## Codex credential resolution
**Path/Symbol:** `src/codex-auth.ts:getCodexCredentials` (120–136); `readCodexAuth` (96–118), `parseCodexRegistryCredentials` (66–94), `extractAccountIdFromJwt` (51–64), `waitForSignal` (17–39), `decodeBase64Url` (41–45); `AUTH_FILE` (6).
**Signature:** `async getCodexCredentials(ctx?: Pick<ExtensionContext, "modelRegistry">, signal?: AbortSignal): Promise<CodexCredentialsWithSource | undefined>`; `readCodexAuth(): CodexCredentials | undefined`; `parseCodexRegistryCredentials(raw: string | undefined): CodexCredentials | undefined`.
**Data Shape:** `CodexCredentials = { accessToken: string, accountId: string }`; `CodexCredentialsWithSource` adds `source: "modelRegistry" | "authFile"`. `AUTH_FILE = join(piAgentDir(), "auth.json")`. The auth file entry is keyed by `"openai-codex"` with `{ type: "oauth", access, accountId|account_id, expires? }`.

### Decisive source
```ts
// getCodexCredentials: registry first, then auth-file fallback
const registryRequest = ctx?.modelRegistry?.getApiKeyForProvider("openai-codex");
const registryToken = registryRequest ? await waitForSignal(registryRequest.catch(() => undefined), signal) : undefined;
const registryCredentials = parseCodexRegistryCredentials(registryToken);
if (registryCredentials) return { ...registryCredentials, source: "modelRegistry" };
const auth = readCodexAuth();
return auth ? { ...auth, source: "authFile" } : undefined;

// readCodexAuth: only accept type=oauth, reject expired
const entry = auth["openai-codex"];
if (entry?.type !== "oauth") return undefined;
if (typeof entry.expires === "number" && Date.now() >= entry.expires) return undefined;

// extractAccountIdFromJwt: base64url-decode the payload, read the OpenAI auth claim
const [, payload] = token.split(".");
const parsed = JSON.parse(decodeBase64Url(payload));
const accountId = parsed["https://api.openai.com/auth"]?.chatgpt_account_id;
```

**Flow:** (1) if a signal is already aborted, throw immediately; (2) ask the model registry for the provider key (wrapped in `waitForSignal` so an abort releases a hung lookup); (3) `parseCodexRegistryCredentials` accepts a JSON object (`access`/`token` + `accountId`/`account_id`) or a plain bearer token whose JWT yields an account id; (4) if that fails, `readCodexAuth` reads `auth.json`, requires `type === "oauth"`, rejects an expired token, and returns trimmed `access` + `accountId`; (5) returns undefined only when both sources are absent.

**Invariant:** the model registry always wins over the auth file; an expired auth-file token is never reused even if the registry lookup fails; a pre-aborted or aborted credential lookup rejects rather than hanging; the access token and account id are always trimmed before use.

**Probe:** `tests/usage.test.ts` (`requestCodexUsage` describe) — `reads isolated auth and sends usage fetch headers` (auth-file `access:"usage-access"`/`accountId:"acct_usage"` → `authorization: "Bearer usage-access"`, `chatgpt-account-id: "acct_usage"`); `uses refreshed model-registry credentials before auth-file fallback` (registry `{access:"registry-access",accountId:"acct_registry"}` wins); `does not reuse a known-expired auth-file token after registry refresh fails` (expired token → undefined, no fetch); `allows an abort signal to release a hung registry credential lookup` and `does not start a credential lookup for an already-aborted request`. Also `tests/image.test.ts` exercises `parseCodexRegistryCredentials` for the image tool. Coverage caveat: `tests/` is excluded from the index by design (`fast-pattern`), so these probes are source-grounded from the on-disk test files, not graph-covered.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-better-openai", query: "getCodexCredentials readCodexAuth parseCodexRegistryCredentials extractAccountIdFromJwt", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the registry-first precedence, the OAuth-type + expiry validation, the JWT account-id extraction, the plain-bearer fallback, and the abort-aware credential wait. Adapt the provider name (`openai-codex`), the auth file path, and the registry API to the host. Omit the pi `modelRegistry`/`ExtensionContext` coupling unless a target provides an equivalent.
