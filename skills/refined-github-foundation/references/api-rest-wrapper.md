<!-- capsule-v2 -->
# REST API Wrapper — how do you wrap fetch() so relative paths resolve to the current repo and errors become human guidance?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** What is the contract of `api.v3` — URL algebra, caching, pagination, and the error taxonomy?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/api.tsx:` `v3uncached` (:179–230), `v3` = memoized wrapper (:232–234), `v3paginated` (:236–252), `v3hasAnyItems` (:254–265), `getError` (:122–177).
**Signature:** `v3(query: string, options?: {ignoreHttpStatus?: boolean|number; method?; body?; headers?; responseFormat?: 'json'|'text'|'base64'}): Promise<AnyObject & {httpStatus, headers, ok}>`.
**Data Shape:** success = parsed body augmented with `{httpStatus, headers, ok}`. Empty bodies arrive as `{content}` (text/base64 formats). Failure = thrown `RefinedGitHubApiError` (multi-line message, optional `richMessage: JSX`, `.response` raw payload).

### Decisive source
```ts
// Relative-path algebra: '/'-prefixed = site-relative; bare = repo-relative
if (!query.startsWith('https')) {
	query = query.startsWith('/') ? query.slice(1)
		: ['repos', getRepo()!.nameWithOwner, query].filter(Boolean).join('/');
}
const url = new URL(query, api3);
```
```ts
// Pagination follows the Link header forever:
const match = /<(?<url>[^<>]+)>; rel="next"/.exec(response.headers.get('link')!);
if (match) query = match.groups!.url; else return;
```

**Flow:** write methods (`method !== 'GET'`) first pass the one-time token↔user identity gate → token attached only if configured → response format switch (JSON default) → status ladder: `ignoreHttpStatus === true || ignoreHttpStatus === status || response.ok` passes with metadata appended; otherwise `throw await getError(body)` which classifies rate-limit ("It may be time for a walk! 🍃"), bad credentials, missing `workflow` scope, fine-grained-token org blocks (with a richMessage link), and a catch-all that embeds the JSON body.
**Invariant:** the repo-relative path form silently depends on being ON a repo page (`getRepo()` throws otherwise) — porters must keep that precondition or always pass absolute paths. Caching is keyed on the FULL argument tuple via `mem(v3uncached, {cacheKey: JSON.stringify})`: identical GETs within one page lifecycle hit cache; anything varying (headers object identity irrelevant) must go through `v3uncached`. `ignoreHttpStatus` accepts either "accept any status" or one specific expected code.
**Probe:** `source/github-helpers/index.test.ts` pins the repo-page context helpers `getRepo`/`buildRepoUrl` used by the URL algebra (`__snapshots__` inline); error strings are exercised end-to-end by features catching `RefinedGitHubApiError` (e.g. `getNextConversationNumber` at `source/github-helpers/get-next-conversation-number.ts:5` consumes `api.v3('issues?per_page=1')`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "api v3 getError v3paginated ignoreHttpStatus", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the wrapper shape for any host-API client: repo-scoped path sugar, metadata-augmented successes, single classified-error funnel. Adapt the base URLs / auth header and the specific error messages. Omit the GraphQL-specific bits (separate capsule) and the JSX richMessage if your UI has no renderer. Direct tests cover the context helpers; the wrapper itself is integration-tested by 300 features — caveat recorded.
