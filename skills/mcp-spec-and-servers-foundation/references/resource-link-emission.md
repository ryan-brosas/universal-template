<!-- capsule-v2 -->
# resource_link emission — how does a tool hand the client POINTERS to server resources instead of inlining their bytes, across static, generated, and session-scoped resources?

**Source:** modelcontextprotocol/servers MIT `main@76d64c82`; Codebase Memory `servers`. **Question:** When must a tool return `{ type: "resource_link", uri, name, ... }` blocks rather than `resource` content, and what URI-construction discipline keeps the pointers resolvable?

## Three registration families, one pointer contract
**Path/Symbol:**
- Static demo resources → links: `src/everything/tools/get-resource-links.ts` (whole file, 86L: count arg 1–10 default 3 :12–19; odd/even text/blob alternation :59–82).
- Generated-resource reference: `src/everything/tools/get-resource-reference.ts` (whole file, 104L: manual enum+integer validation :52–70; three-block result :72–89).
- Session-created artifacts: `src/everything/tools/gzip-file-as-resource.ts` :95–124 via `resources/session.ts` helpers (`getSessionResourceURI`, `registerSessionResource` — full contract in `session-resource-reregistration.md`).

**Signature:** link block = `{ type: "resource_link", uri, name, description?, mimeType? }`. URI builders from `resources/templates.ts`: `textResourceUri(resourceId)` / `blobResourceUri(resourceId)` (:118/:126) — scheme-differentiated so read handlers can dispatch on shape.

**Data Shape:** intro `text` block + N link blocks; every link carries enough metadata (`mimeType`, human description) for a client UI to render it WITHOUT reading the resource.

### Decisive source
```ts
// get-resource-links.ts:59-82 — build URIs through the shared builders, never by string concat
for (let resourceId = 1; resourceId <= count; resourceId++) {
  const isOdd = resourceId % 2 === 0;
  const uri = isOdd ? textResourceUri(resourceId) : blobResourceUri(resourceId);
  const resource = isOdd ? textResource(uri, resourceId) : blobResource(uri, resourceId);
  content.push({
    type: "resource_link",
    uri: resource.uri,
    name: `${isOdd ? "Text" : "Blob"} Resource ${resourceId}`,
    description: `Resource ${resourceId}: ${resource.mimeType === "text/plain" ? "plaintext resource" : "binary blob resource"}`,
    mimeType: resource.mimeType,
  });
}
```
```ts
// get-resource-reference.ts:52-61 — belt-and-braces validation BEFORE building the pointer
const { resourceType } = args;
if (!RESOURCE_TYPES.includes(resourceType)) { throw new Error(`Invalid resourceType: ${args?.resourceType}. Must be ${RESOURCE_TYPE_TEXT} or ${RESOURCE_TYPE_BLOB}.`); }
const resourceId = Number(args?.resourceId);
if (!Number.isFinite(resourceId) || !Number.isInteger(resourceId) || resourceId < 1) { throw new Error(`Invalid resourceId: ${args?.resourceId}. Must be a finite positive integer.`); }
```

**Flow:** tool computes WHICH resources to point at (static enumeration / generated template instance / just-created session artifact) → constructs URIs ONLY through shared builders or the session helper → emits `resource_link` blocks (optionally with an intro text block) → client later calls `resources/read`; the embedded-resource variant returns `{ type: "resource", resource }` INSIDE the result when bytes are wanted inline (:get-resource-reference :80–88, gzip `outputType:"resource"`).

**Invariants:**
1. **URIs must come from the same builders the read handlers dispatch on** — a link whose URI the reader can't resolve is a dangling pointer; hand-built URI strings are the classic port bug.
2. **Validate args manually even when zod declared them** when defaults may bypass parsing (`args.resourceType` used raw) — finite/integer/≥1 checks precede URI construction.
3. **Links point, results carry**: choosing `resource_link` vs embedded `resource` is a payload-size/lifetime decision (session artifacts default to `resourceLink` so clients fetch lazily within the session).
4. Prompt-side twin: prompts embed resources as `{ role, content: { type: "resource", resource } }` message blocks (`prompts/resource.ts` :73–90), NOT as resource_links — don't confuse the two surfaces.

**Probe:** `src/everything/__tests__/tools.test.ts:368–465` — pins link counts, odd/even text-vs-blob alternation, default count 3 (:368–414); invalid resourceType and invalid resourceId rejection (:415–465). `__tests__/prompts.test.ts` pins the prompt-embedded variant.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "resource_link textResourceUri blobResourceUri mimeType pointer", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt builder-constructed URIs, metadata-complete links, and manual numeric validation ahead of pointer construction; adapt the URI schemes and catalog logic to your product; omit the demo alternation gimmick. Complements `session-resource-reregistration.md` (artifact lifecycle) — this capsule covers the RESULT-SHAPE side of handing clients resource pointers.
