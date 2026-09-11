<!-- capsule-v2 -->
# Resource-URL matching & fragment stripping — how does RFC 8707 resource-indicator comparison work without false subpath positives?

**Source:** typescript-sdk MIT `main@3924de9`; Codebase Memory `mnt-hdd-utopia-inspo-mcp-typescript-sdk`. **Question:** How should a token endpoint or RS compare a requested `resource` against its configured resource URL?

## RFC 8707 helpers
**Path/Symbol:** `packages/core-internal/src/shared/authUtils.ts`: `resourceUrlFromServerUrl` (:11-15), `checkResourceAllowed` (:27-57).
**Signature:** `resourceUrlFromServerUrl(url: URL | string): URL`; `checkResourceAllowed({requestedResource, configuredResource}): boolean`.
**Data Shape:** fragment stripped (`resourceURL.hash = ''` — RFC 8707 §2 "MUST NOT include a fragment component"), everything else preserved; match = same origin + requested path startswith configured path with BOTH sides slash-normalized.

### Decisive source
```ts
// :48-56 the trailing-slash guard
const requestedPath = requested.pathname.endsWith('/') ? requested.pathname : requested.pathname + '/';
const configuredPath = configured.pathname.endsWith('/') ? configured.pathname : configured.pathname + '/';
return requestedPath.startsWith(configuredPath);
```

**Flow:** `resourceUrlFromServerUrl` normalizes any server URL into a legal resource indicator (token endpoints call this when echoing `resource` into tokens/metadata). `checkResourceAllowed`: origin mismatch ⇒ false; shorter-requested-path ⇒ false; then the normalized prefix check. The comment names the bug class: without normalization `/api123` would prefix-match configured `/api`.

**Invariant:** prefix comparison MUST be segment-safe (slash-pad both sides) — raw startsWith is the classic path-confusion hole; origin equality is exact scheme+host+port, so no downgrade tricks. Fragment stripping happens at NORMALIZATION time, not at comparison, so stored resources are already canonical.

**Probe (direct tests):** `packages/core-internal/test/shared/authUtils.test.ts` — 'should remove fragments' :5, 'should keep everything else unchanged' :19, describe 'resourceMatches' :35 (identical/different-path/domain/port cases).

**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-mcp-typescript-sdk", query: "resourceUrlFromServerUrl checkResourceAllowed fragment", limit: 3 });
```

## Verdict
Adopt both helpers verbatim (12 + 30 lines, zero deps beyond URL); adapt naming to your auth utils; omit nothing.
