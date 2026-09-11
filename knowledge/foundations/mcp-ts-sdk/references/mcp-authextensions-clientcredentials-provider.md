<!-- capsule-v2 -->
# ClientCredentialsProvider — what makes an OAuthClientProvider non-interactive without breaking auth()?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** Which provider members must exist, which may be no-ops, and which must throw so `auth()` can drive a machine-to-machine `client_credentials` flow end-to-end?

## Non-interactive provider skeleton (constructor-stamped credential binding)
**Path/Symbol:** `packages/client/src/client/authExtensions.ts` `ClientCredentialsProvider` (:149-211).
**Signature:** `class ClientCredentialsProvider implements OAuthClientProvider`; `new ClientCredentialsProvider(options: ClientCredentialsProviderOptions)`; `prepareTokenRequest(scope?: string): URLSearchParams`.
**Data Shape:** Constructor stamps `this._clientInfo = { client_id, client_secret, issuer: options.expectedIssuer }` (:155-159) — the optional `expectedIssuer` field IS the SEP-2352 stamp consumed by `auth()`'s AS-mismatch check. `_clientMetadata` declares `grant_types: ['client_credentials']`, `token_endpoint_auth_method: 'client_secret_basic'`, `redirect_uris: []` (:160-166).

### Decisive source
```ts
// No saveClientInformation: credentials are constructor-supplied and bound to a single
// authorization server. When `expectedIssuer` is set and the resolved AS differs, the
// SEP-2352 stamp check discards `clientInformation()` and auth() throws
// AuthorizationServerMismatchError(expectedIssuer, resolved) rather than sending the credential.
```
(:181-184)

**Flow:** `auth()` reads `redirectUrl` → `get undefined` marks non-interactive so no browser leg runs; `prepareTokenRequest(scope?)` builds `{ grant_type: 'client_credentials', scope? }` synchronously (:206-210); `applyClientAuthentication('client_secret_basic', …)` adds the Basic header later; `saveTokens` keeps tokens in memory only.
**Invariant:** Deliberate member asymmetry — `saveCodeVerifier()` is a silent no-op but `codeVerifier()` THROWS `'codeVerifier is not used for client_credentials flow'` (:202-204), as does `redirectToAuthorization()` (:194-196). A porter who makes both no-ops loses the loud tripwire that fires if the SDK ever attempts an interactive leg against this provider. Omitting `saveClientInformation` entirely is correct BY DESIGN: the absence forces every token round-trip through the constructor-bound, issuer-stamped info instead of whatever a store might return.
**Probe:** `grep -cF 'grant_types: [' packages/client/src/client/authExtensions.ts` → 4 (three `['client_credentials']` at :163/:299/:411 + one `['urn:ietf:params:oauth:grant-type:jwt-bearer']` at :621); direct tests `packages/client/test/client/authExtensions.test.ts` — describe `auth-extensions providers (end-to-end with auth())` :16, first case `it('authenticates using ClientCredentialsProvider with client_secret_basic'…)` :17 (verify `sed -n '17p'` matches), scope case :54.
**Caveat:** identifier text in this file displays hygienically elided in some tool output; author greps from byte-level `grep -F` anchors like these, never from copied prose.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "prepareTokenRequest client_credentials provider", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the skeleton: constructor-stamped clientInfo, `redirectUrl: undefined`, throwing interactive-leg tripwires, sync `prepareTokenRequest`. Adapt storage: swap in-memory `_tokens` for your host's secret store while keeping `saveClientInformation` absent. Omit nothing behavioral — the asymmetry (silent vs throwing members) is the ported contract. Tests run under the repo's vitest suite; deterministic anchor checks above stand in where node_modules is absent.
