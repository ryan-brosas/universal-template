<!-- capsule-v2 -->
# GraphQL Wrapper — how do you keep GraphQL queries short when every call needs the same repo variables and error handling?

**Source:** refined-github MIT `main@3bbe6088fe301d0d5cf1ae751a49307005762a68`; Codebase Memory `refined-github`. **Question:** How does `api.v4` auto-inject `$owner`/`$name`, wrap bare queries, and decide what is cacheable?

## Connected graph-selected seam
**Path/Symbol:** `source/github-helpers/api.tsx:` `v4uncached` (:267–340), `v4` custom-cacheKey wrapper (:342–354), `escapeKey` (:58).
**Signature:** `v4(query: string, options?: {allowErrors?: boolean; variables?: JsonObject}): Promise<AnyObject>` (the `data` field only).
**Data Shape:** input query may be a bare selection set (`{user(login:"x"){name}}`) or a full operation; output = parsed `data`; failures throw `RefinedGitHubApiError('GraphQL:', ...errorMessages)` unless `allowErrors`.

### Decisive source
```ts
// GraphQL uses POST for everything, so check the query type instead of the HTTP method:
if (/^\s*mutation[\s({]/.test(query)) await assertCurrentUser();

const currentRepoIfAny = getRepo(); // Don't destructure, it's undefined outside repos
query = query.replace('repository() {', () => 'repository(owner: $owner, name: $name) {');

// Automatically provide common variables ONLY when used — GraphQL rejects unused ones.
const variables: JsonObject = {};
const parameters: string[] = [];
if (query.includes('$owner')) { variables.owner = currentRepoIfAny!.owner; parameters.push('$owner: String!'); }
if (query.includes('$name'))  { variables.name  = currentRepoIfAny!.name;  parameters.push('$name: String!'); }
Object.assign(variables, options.variables);

const fullQuery = /^\s*(?:query|mutation)/.test(query) ? query
	: parameters.length === 0 ? `query {${query}}`
	: `query (${parameters.join(',')}) {${query}}`;
```
```ts
// Cache key MUST include the repo when globals are used — or page A's data leaks to page B:
if (query.includes('repository() {') || query.includes('owner: $owner, name: $name')) {
	key.push(getRepo()?.nameWithOwner);
}
```

**Flow:** token required up-front for ALL v4 calls → mutation-regex identity gate → `repository()` sugar rewritten to explicit variables → used-only variable injection → bare selections wrapped in a synthetic `query (...) {}` envelope → POST → `{data, errors}` destructure: errors present + !allowErrors ⇒ throw with all messages joined; ok ⇒ return data; else `getError`.
**Invariant:** the memo cache key includes `getRepo()?.nameWithOwner` IFF the query touches global state — forgetting this forks nothing but silently returns WRONG-repo results on SPA navigation (issue #5821). Variables are injected by substring detection (`query.includes('$owner')`), so a porter renaming variables must update both the regex-sugar and the detection pairs. `escapeKey('_'+String(keys).replace(non-alnum,'_'))` exists for building alias names GraphQL accepts.
**Probe:** `source/github-helpers/index.test.ts` pins `getRepo` parsing feeding the variable injection; mutation/allowErrors behavior is exercised via features using `.gql` files (e.g. `does-file-exist.gql`, `is-conversation-locked.gql` imported next to their consumers). Caveat: wrapper itself untested directly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "refined-github", query: "v4uncached repository owner name variables allowErrors", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the variable-auto-injection + repo-aware cache-key pattern for any GraphQL client bound to a "current entity" context. Adapt the sugar syntax and variable names. Omit the REST-specific parts. Coverage caveat recorded (integration-tested only).
