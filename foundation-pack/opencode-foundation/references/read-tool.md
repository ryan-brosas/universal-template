<!-- capsule-v2 -->
# Read tool — offset/limit paginated file + directory reads

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how does a read tool bound memory on large files/dirs and report "more" so the model pages through?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/read.ts` (386 lines): `Parameters` (:28-40), `ReadTool` (:64), `lines` (:137-179), `execute` (:266-339).
**Signature:** `execute({filePath, offset?, limit?}, ctx)` — `offset`/`limit` are `NonNegativeInt` (optional); `DEFAULT_READ_LIMIT`; reads lines `[offset-1, offset-1+limit]`, returns `{raw, count, cut, more, offset}`.
**Data Shape:** `Parameters = {filePath: string, offset?: number, limit?: number}`; output = `"${i+offset}: ${line}"` per line + `(Showing N of M entries. Use 'offset' to read beyond entry X)` when truncated.

### Decisive source
```ts
const limit = params.limit ?? DEFAULT_READ_LIMIT
const offset = params.offset || 1
const start = offset - 1
const sliced = items.slice(start, start + limit)
// output += `(Showing ${sliced.length} of ${items.length} entries. Use 'offset' parameter to read beyond entry ${offset + sliced.length})`
// offset out of range -> Error(`Offset ${offset} is out of range for this file (${count} lines)`)
```

**Flow:** resolve path → if directory, list entries (paginated, with "use offset" hint); if file, read lines `[offset-1, offset-1+limit]` with a `cut`/`more` flag; out-of-range offset errors instructively.
**Invariant:** offset/limit are non-negative ints (coerced, not `z.coerce.number()`); reads are bounded (never whole-file); the "more" hint tells the model to page with offset.
**Probe:** `packages/opencode/test/tool/read.test.ts` (offset/limit pagination; directory listing; out-of-range offset error; `more` flag set when truncated).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "ReadTool read offset limit lines paginate more", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the offset/limit paginated read with a `more` flag and "use offset to read beyond" hint; adapt the default limit and directory-listing format to host; omit the Effect service wiring unless the target uses Effect.
