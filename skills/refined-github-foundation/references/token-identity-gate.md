<!-- capsule-v2 -->
# Token Identity & Scope Gate — how do you stop a stale personal token from writing as the wrong user, and verify scopes before acting?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the write-guard ladder that maps API failures to actionable messages, and how are token scopes probed?

## Connected graph-selected seam
Cluster #2 in the architecture (`getToken; v4uncached; init; baseApiFetch; expectTokenScope`, cohesion .81).

**Path/Symbol:** `source/github-helpers/api.tsx:` `assertCurrentUser` (:90–109); `source/github-helpers/github-token.ts:` `tokenUser` CachedFunction (:407–418), `parseTokenScopes` (:443–463), `getTokenInfo` (:470–482), `expectTokenScope` (:484–498), `expectToken` (:420–427); storage `source/options-storage.ts:getToken` (:273–280).
**Signature:** `assertCurrentUser(): Promise<void>` (onetime); `getTokenInfo(apiBase, token): Promise<{scopes: string[]; expiration?: string}>`; `expectTokenScope(scope): Promise<void>`.
**Data Shape:** `tokenUser` caches `login` per `hashString(apiBase+'-'+token)` for **365 days** ("the exact token is forever associated to the user"); scope list carries synthetic entries `valid_token`, `unknown` (fine-grained tokens omit `X-OAuth-Scopes`), plus implied grants (`repo`⇒`public_repo`, `project`⇒`read:project`).

### Decisive source
```ts
// One-time gate: block writes when the token belongs to someone else
const currentTokenUser = await tokenUser.get(api3, personalToken);
if (currentTokenUser !== loggedInUser) {
	throw new RefinedGitHubApiError(
		'API call blocked.',
		`Your token belongs to "${currentTokenUser}" but you are logged in as "${loggedInUser}".`,
		'Update your token in the Refined GitHub options.',
	);
}
```
```ts
// Fine-grained tokens don't send X-OAuth-Scopes — absence means valid-but-unknown, NOT invalid:
if (!scopesHeader) return ['valid_token', 'unknown'];
// Safari can't parse GitHub's expiration format without normalization (#9043):
expiration?.replace(' ', 'T').replace(' UTC', 'Z');
```

**Flow:** any non-GET v3 / mutation v4 call → `assertCurrentUser()` (memoized once per page): fetch token's login (cached year-long) and compare against the DOM-derived logged-in user → mismatch throws BEFORE the request. Separately, features that need a specific capability call `expectTokenScope('workflow' | …)` → GET root with `cache:'no-store'` → read `X-OAuth-Scopes` + `GitHub-Authentication-Token-Expiration`.
**Invariant:** the guard fires only on WRITES — reads stay cheap and anonymous-friendly. The scope parser treats a MISSING header as success-with-unknown-scopes (fine-grained PATs), never as an error. `expectToken` vs `hasValidGitHubComToken`: one throws for missing config, the other probes validity over the network returning boolean — porters conflate these constantly.
**Probe:** no unit test (network-bound); behavior pinned by consumption: `requiresToken: true` loaders funnel through `expectToken` (feature-manager :218–220); the blocked-write message strings are stable UX contract cited verbatim at api.tsx:103–108. Coverage caveat recorded.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "assertCurrentUser tokenUser parseTokenScopes expectTokenScope", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the write-time identity gate + synthetic-scope fallback for any client storing long-lived user tokens alongside a logged-in session. Adapt the cache TTL and message copy. Omit Safari-specific date normalization if not targeting Safari. No direct test — caveat recorded.
