<!-- capsule-v2 -->
# ToolAnnotations Hints — how do readOnly/destructive/idempotent/openWorld hints work, and why are they never authorization?

**Source:** modelcontextprotocol/specification MIT `main@4df2d6b`; Codebase Memory `modelcontextprotocol`. **Question:** What does each tool behavior hint mean exactly (including cross-conditional defaults), and what may a client safely do with them?

## The five hint properties
**Path/Symbol:** `schema/draft/schema.ts` (`ToolAnnotations` :1912–1954, interface doc :1900–1908); prose `docs/specification/draft/server/tools.mdx` :302–307.

**Data Shape:** optional object on `Tool`: `{ title?, readOnlyHint?, destructiveHint?, idempotentHint?, openWorldHint? }`. All booleans default to their CONSERVATIVE reading when absent: readOnly=false, destructive=true, idempotent=false, openWorld=true. Two hints are conditional: `destructiveHint` and `idempotentHint` are "meaningful only when `readOnlyHint == false`" — a read-only tool is by definition non-destructive and repeatable, so the other flags carry no information there.

### Decisive source
```ts
// schema.ts:1918-1922
// If true, the tool does not modify its environment.
readOnlyHint?: boolean;            // Default: false

// schema.ts:1925-1930
// If true, the tool may perform destructive updates to its environment.
// If false, the tool performs only additive updates.
// (This property is meaningful only when `readOnlyHint == false`)
destructiveHint?: boolean;         // Default: true

// schema.ts:1934-1939
// If true, calling the tool repeatedly with the same arguments
// will have no additional effect on its environment.
// (This property is meaningful only when `readOnlyHint == false`)
idempotentHint?: boolean;          // Default: false

// schema.ts:1943-1948
// If true, this tool may interact with an "open world" of external
// entities. If false, the tool's domain of interaction is closed.
openWorldHint?: boolean;           // Default: true

// schema.ts:1903-1908 — the governing note:
// all properties in `ToolAnnotations` are **hints** ... not guaranteed to
// provide a faithful description of tool behavior ... Clients should never
// make tool use decisions based on `ToolAnnotations` received from
// untrusted servers.
```

**Flow (intended client use):** `tools/list` → client renders confirm-dialogs / batching policy from hints — e.g. auto-run `readOnlyHint: true` tools without confirmation ONLY for trusted servers, batch/queue destructive ones behind explicit approval, dedupe retries freely when `idempotentHint: true`, scope network access expectations via `openWorldHint` → actual enforcement comes from the client's own permission model + user consent, NEVER from the annotations themselves.

**Invariant:** hints are advisory metadata from the SERVER about itself — the same party being gated — so they can be wrong or lied to. The MUST in tools.mdx (:305–307) makes treating untrusted annotations as authorization a spec violation. A porter who skips confirmation because `destructiveHint: false`, or who assumes absent hints mean "safe", breaks trust & safety requirements.

**Probe:** no runtime tests in the spec repo; machine-checkable anchor is `ToolAnnotations` in `schema/draft/schema.ts` (+ example JSONs). Coverage caveat recorded honestly.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "modelcontextprotocol", name_pattern: "ToolAnnotations", limit: 10 });
```

## Verdict
Adopt the four-hint vocabulary with conservative defaults and the readOnly-conditional semantics for UX gating on TRUSTED servers; adapt your consent UX and batching policy to host; omit using hints as authorization or access control (hard MUST against it), and omit `title` as a security signal (explicitly unfaithful-description territory).
