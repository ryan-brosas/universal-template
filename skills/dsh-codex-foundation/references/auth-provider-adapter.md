<!-- capsule-v2 -->
# Provider auth adapter — one Codex OAuth provider with secret-free status

**Source:** dsh-codex Apache-2.0 `main@e3e54e206f7c829503c7e6eed378643ba0416792`; Codebase Memory `dsh-codex`. **Question:** how should a provider plugin expose native OAuth, logout, and non-secret status through one host-neutral adapter without widening the credential boundary?

## loginOpenAICodex, logoutOpenAICodex, and openAICodexAuthStatus
**Path/Symbol:** `src/auth.ts:24-31 loginOpenAICodex`, `src/auth.ts:37-41 logoutOpenAICodex`, `src/auth.ts:48-55 openAICodexAuthStatus`.
**Signature:** `loginOpenAICodex(interaction: AuthInteraction, store?: OpenAICodexCredentialStore): Promise<void>`; `logoutOpenAICodex(store?: OpenAICodexCredentialStore): Promise<void>`; `openAICodexAuthStatus(store?: OpenAICodexCredentialStore): Promise<OpenAICodexAuthStatus>`.
**Data Shape:** Login receives provider-native `AuthInteraction` and a single-provider credential store. The adapter selects `OPENAI_CODEX_PROVIDER = 'openai-codex'` and `'oauth'`; status returns only `{ authenticated: boolean; expiresAt?: Date }` and never returns access, refresh, or account identifiers.

### Decisive source
```ts
export async function loginOpenAICodex(interaction: AuthInteraction, store = new OpenAICodexCredentialStore()): Promise<void> {
  const models = createModels({ credentials: store })
  models.setProvider(openaiCodexProvider())
  await models.login(OPENAI_CODEX_PROVIDER, 'oauth', interaction)
}

export async function logoutOpenAICodex(store = new OpenAICodexCredentialStore()): Promise<void> {
  await store.delete(OPENAI_CODEX_PROVIDER)
}

const credential = await store.read(OPENAI_CODEX_PROVIDER)
return credential?.type === 'oauth'
  ? { authenticated: true, expiresAt: new Date(credential.expires) }
  : { authenticated: false }
```

**Flow:** construct the pi-ai model registry around the caller-supplied store → install the Codex provider → delegate the complete OAuth interaction; logout delegates only the owned provider id to the store; status reads that same id and projects a boolean plus expiry date.
**Invariant:** the adapter owns exactly one provider route and never crosses the store boundary with token-bearing data; a missing/non-OAuth credential is signed out; expiry is observational only, so status does not refresh or mutate credentials.
**Probe:** `tests/bin.spec.ts:189-225` (CLI status projects signed-in/signed-out JSON and asserts no expiry/account/access/refresh secrets) plus `tests/auth-routes.spec.ts:395-435` (web boundary consumes the status projection). No dedicated unit test imports `src/auth.ts` directly; deterministic source probe below covers the three exact delegations.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: 'dsh-codex', qn_pattern: 'dsh-codex\\.src\\.auth\\.(loginOpenAICodex|logoutOpenAICodex|openAICodexAuthStatus)', limit: 10, fields: ['signature', 'name', 'file'] });
```

## Verdict
Adopt the thin provider-auth adapter and its secret-free status projection. Adapt the provider factory, owned id, and host credential interface; keep refresh/exchange mechanics inside the provider-native auth implementation and keep status read-only. Coverage: `src/auth.ts` is `no_recorded_issue` with `metadata_match`; the direct CLI/auth-route tests are covered, while the adapter itself has no dedicated test and was source-confirmed plus deterministically probed.
