<!-- capsule-v2 -->
# Resource templates invisible to list — how do you expose infinite dynamic resources without breaking `resources/list`, and where do template completers attach?

**Source:** modelcontextprotocol/servers MIT `main@76d64c822f5125032f89eb71dbdb94e42b434821` (src/everything); Codebase Memory `servers`. **Question:** How does a URI-template resource register so ANY positive-integer ID resolves while the list endpoint stays clean — and how are per-variable completers wired?

## Template with list:undefined + per-variable complete map
**Path/Symbol:** `src/everything/resources/templates.ts` (whole file, 211L: completer factories :27–72; URI construction :74–78; content builders :86–111; `parseResourceId` :139–155; `registerResourceTemplates` :171–211). Registration uses SDK `new ResourceTemplate(uriTemplate, { list: undefined, complete: { resourceId: cb } })`.

**Signature:** two registrations — `"demo://resource/dynamic/text/{resourceId}"` (mimeType text/plain) and `.../blob/{resourceId}` (application/octet-stream); read callback `(uri, variables) => { contents: [builder(uri, parseResourceId(uri, variables))] }`; completers `(value: string) => string[]` return `[value]` for finite positive integers else `[]` (:67–72).

**Data Shape:** prompt arguments are STRINGS ONLY — the in-file comment pins it (:40–42: "prompt arguments can only be strings since type is not field of PromptArgument" + schema URL), so `resourceIdForPromptCompleter` accepts a string and the consumer re-numbers it. Blob payloads are base64 (`Buffer.from(...).toString("base64")` :102–105).

### Decisive source
```ts
// src/everything/resources/templates.ts:171-190 (text twin; blob identical shape)
server.registerResource(
  "Dynamic Text Resource",
  new ResourceTemplate(textUriTemplate, {
    list: undefined,                                        // ← template NEVER appears in resources/list
    complete: { resourceId: resourceIdForResourceTemplateCompleter },
  }),
  { mimeType: "text/plain", description: "...{resourceId} variable, which must be an integer." },
  async (uri, variables) => {
    const resourceId = parseResourceId(uri, variables);
    return { contents: [textResource(uri, resourceId)] };
  }
);

// :139-155 — validation lives at READ time, not list time
const parseResourceId = (uri: URL, variables: Record<string, unknown>) => {
  const uriError = `Unknown resource: ${uri.toString()}`;
  if (uri.toString().startsWith(textUriBase) &&
      uri.toString().startsWith(blobUriBase)) {             // unreachable-by-construction guard
    throw new Error(uriError);
  } else {
    const idxStr = String((variables as any).resourceId ?? "");
    const idx = Number(idxStr);
    if (Number.isFinite(idx) && Number.isInteger(idx) && idx > 0) return idx;
    throw new Error(uriError);                              // "Unknown resource" ⇒ maps to -32602 upstream
  }
};
```

**Flow:** `resources/templates/list` returns the two template descriptors (with mimeType + description) → client builds concrete URIs (`demo://resource/dynamic/text/7`) → `resources/read` matches the template, SDK interpolates `{resourceId}` into `variables`, read callback validates (finite/integer/>0) and fabricates timestamped content on demand → completion requests route to the per-variable map (`complete: { resourceId }`) so clients autocomplete IDs inside the template.

**Invariant:** `list: undefined` keeps template-instantiated resources OUT of `resources/list` (in-file doc :160–162: "List resources method will not return these resources") — a porter who supplies a list callback here floods clients with infinite entries; one who validates at REGISTRATION instead of READ breaks the infinite-ID contract (any positive integer must resolve). Validation errors throw plain `Error("Unknown resource: ...")` and rely on the host mapping to `-32602 Invalid params` (spec-side `resources-surface` capsule: not-found is -32602, never empty contents).

**Probe:** `src/everything/__tests__/resources.test.ts` — `registerResourceTemplates` registers exactly 2 templates (:142–168, mock-server count pinned); `resourceIdForResourceTemplateCompleter('1')→['1']`, `('0')/('-5')/('not-a-number')→[]` (:129–140); URIs round-trip `demo://resource/dynamic/{text,blob}/N` (:36–58); base64 decodes back to source text (:90–98).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "servers", query: "ResourceTemplate registerResource completable parseResourceId", limit: 10, fields: ["name", "file"] });
```

## Verdict
Adopt template-with-list-undefined for unbounded resource families, read-time integer validation throwing "Unknown resource", string-only prompt-arg completers, and per-variable `complete` maps; adapt URI scheme and content fabrication to your domain; omit a list callback on such templates (breaks listing) and omit numeric prompt args (schema forbids them).
