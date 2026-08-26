<!-- capsule-v2 -->
# Grep & glob tools — ripgrep-backed content and file search

**Source:** opencode MIT `<branch>@<commit>`; Codebase Memory `opencode`. **Question:** how do content-search (grep) and file-search (glob) tools stay fast and permission-gated?

## Connected graph-selected seam
**Path/Symbol:** `packages/opencode/src/tool/grep.ts` (115 lines): `Parameters` (:10-18), `GrepTool` (:20); `packages/opencode/src/tool/glob.ts` (76 lines): `Parameters` (:10-17), `GlobTool` (:17).
**Signature:** `grep({pattern, path?, include?})` — regex content search, `include` file pattern (`*.js`, `*.{ts,tsx}`); `glob({pattern, path?})` — glob file match.
**Data Shape:** grep params `{pattern: string, path?: string, include?: string}`; glob params `{pattern: string, path?: string}`; both back `Ripgrep` from `@opencode-ai/core/ripgrep`.

### Decisive source
```ts
// grep.ts
export const Parameters = Schema.Struct({
  pattern: Schema.String,                       // regex content search
  path: Schema.optional(Schema.String),         // dir to search (defaults to cwd)
  include: Schema.optional(Schema.String),      // '*.js', '*.{ts,tsx}'
})
// glob.ts — path description warns: OMIT the field for default, don't pass "undefined"/"null"
export const Parameters = Schema.Struct({
  pattern: Schema.String,                       // glob pattern
  path: Schema.optional(Schema.String),         // dir to search (defaults to cwd)
})
```

**Flow:** grep runs a regex over file contents (optionally filtered by `include`); glob matches files by glob pattern; both default to the cwd and back `Ripgrep`. Both are read-only (no mutation), permission-gated like other tools.
**Invariant:** reads are bounded and permission-gated; `include` filters grep to a file set; glob's path is omitted for default (never "undefined"/"null").
**Probe:** `packages/opencode/test/tool/grep.test.ts` + `glob.test.ts` (regex match in contents; include filter; glob pattern match; permission gate invoked).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "GrepTool GlobTool ripgrep pattern include search", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the ripgrep-backed grep/glob tools with include filtering and cwd-default paths; adapt the regex/glob dialect to host; omit the Effect service wiring unless the target uses Effect.
