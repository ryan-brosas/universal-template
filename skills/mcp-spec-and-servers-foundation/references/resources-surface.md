<!-- capsule-v2 -->
# Resources Surface — how do resources/list, resources/read, and templates behave, and which result rules does a server author get wrong?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What is the exact contract for exposing data resources — listing, templates, reading (including multi-content + MRTR), change notifications, and the error semantics for missing URIs?

## Listing, templates, reading
**Path/Symbol:** `docs/specification/draft/server/resources.mdx` (whole; capabilities :39–82; resources/list :85–132; resources/read :134–179; templates :181–230; list-changed :232–242; subscriptions :244–267; data types :298–364; URI schemes :366–400; error handling :402–426; security :428–435); wire types `schema/draft/schema.ts` (`ListResourcesRequest` :1121–1131, `ListResourcesResult` :1133–1143, `Resource` :1441–1479, `ResourceTemplate` :1481–1512, `ResourceContents` :1514–1533, `TextResourceContents` :1535–1546, `BlobResourceContents` :1548–1564, `ResourceUpdatedNotification` :1411–1439).

**Data Shape:** capability `resources: { listChanged?: bool, subscribe?: bool }` — features independent, may be declared together or neither; empty object legal. `Resource` = `{ uri, name, title?, description?, mimeType?, size?, icons? }`. `ResourceTemplate` swaps `uri` for `uriTemplate` (RFC6570, e.g. `file:///{path}`). `ResourceContents` = `{ uri, mimeType? }` + exactly one of `text` (TextResourceContents) or `blob` (base64, BlobResourceContents).

### Decisive source
```md
# resources.mdx:74-81 (the stability invariant)
Servers that declare the `resources` capability MUST respond to
`resources/list` requests with the set of resources currently available to
the requesting client. This set MAY be empty and MAY change over time,
but MUST NOT vary per-connection or as a side effect of other requests on
the connection. The set MAY vary by the authorization presented on the
request — since credentials are per-request input, not connection state.

# resources.mdx:404-410 (missing-resource error semantics)
If the requested resource does not exist, servers MUST return a JSON-RPC
error with code `-32602` (Invalid Params). Servers SHOULD return `-32603`
for internal errors. For backwards compatibility, clients SHOULD also
accept `-32002` as a resource not found error. Servers MUST NOT return an
empty `contents` array for a non-existent resource. An empty array is
ambiguous—it could mean the resource exists but has no content, or that it
doesn't exist at all.
```

**Flow:** `resources/list` (+cursor pagination, ttlMs/cacheScope caching) → `resources/templates/list` → `resources/read` with `{uri}` → result carries `contents[]` (a server MAY return MULTIPLE contents for one read, e.g. a directory read returns several files) → optional `subscriptions/listen` with `notifications.resourceSubscriptions` filter → server emits `notifications/resources/updated` carrying `_meta["io.modelcontextprotocol/subscriptionId"]` + `uri`.

**MRTR applies:** `resources/read` MAY answer `InputRequiredResult` (e.g. ask for credentials before reading); the client retries with `inputResponses` (+`requestState`) under a NEW request id.

**URI scheme guidance:** `https://` SHOULD be used ONLY when the client can fetch the resource directly from the web without the server (otherwise prefer another/custom scheme even if the server itself downloads over the internet); `file://` marks filesystem-like resources (need not map to a real FS; XDG MIME types like `inode/directory` allowed for directories); custom schemes MUST follow RFC3986.

**Annotations:** resources/templates/content blocks share `{ audience?: ("user"|"assistant")[], priority?: 0..1, lastModified?: ISO-8601 }` — hints for client filtering/prioritization/display, never guarantees.

**Invariant:** list results are connection-stable (vary by auth, never by connection identity or request side effects); a missing resource is a `-32602` protocol error, NEVER `contents: []`. A porter who returns an empty contents array for a nonexistent URI, whose list output flickers between connections, or who embeds binary data as text breaks the contract.

**Probe:** no runtime tests in the spec repo (docs + wire schema only); machine-checkable anchors are the `Resource*` types in `schema/draft/schema.ts` + `scripts/validate-examples.ts`. Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "ListResourcesResult|ResourceTemplate|TextResourceContents|BlobResourceContents", limit: 10 });
```

## Verdict
Adopt the three-request surface (`list` / `templates/list` / `read`), connection-stable listings, multi-content reads, `-32602`-not-found with no-empty-array rule, and opt-in `listChanged`/`subscribe` features; adapt your URI scheme layout, storage backend, and annotation policy to host; omit per-connection list variation (forbidden) and stdio-specific resource behavior (n/a).
