<!-- capsule-v2 -->
# FileSystemSearch dual backend — construction-time engine selection with fail-open

**Source:** opencode MIT `dev@03521003fafd`; Codebase Memory `opencode`. **Question:** how do you offer two search engines (native + subprocess) behind one interface without a runtime fork, and degrade safely when the native one is unavailable?

## Connected graph-selected seam
**Path/Symbol:** `packages/core/src/filesystem/search.ts`: `ripgrepLayer` (:26-77), `fffLayer` (:79-160), selection `Layer.unwrap` (:162), `find` fuzzysort (:64-76).
**Signature:** `Interface = {find(FindInput) => Entry[], glob(GlobInput) => Entry[], grep(GrepInput) => Match[]}`; `Service = "@opencode/v2/FileSystem/Search"`.
**Data Shape:** ripgrepLayer state = `{files: string[], directories: string[]}` built by a forked full-tree `rg find` at layer init (limit MAX_SAFE_INTEGER for vcs roots, else 100_000); fffLayer wraps the native `Fff.create` handle with `{pageIndex, pageSize}` paged calls and a 1_500ms grep time budget.

### Decisive source
```ts
const layer = Layer.unwrap(Effect.sync(() =>
  Flag.OPENCODE_DISABLE_FFF || !Fff.available() ? ripgrepLayer : fffLayer))
...
// fffLayer init failure is fail-open:
Effect.catch((error) => Effect.logWarning("failed to initialize fff", { error }).pipe(Effect.as(undefined)))
if (!result?.ok) { ... return Service.of({ find: () => Effect.succeed([]), glob: () => Effect.succeed([]), grep: () => Effect.succeed([]) }) }
```

**Flow:** selection happens ONCE at layer construction (`Layer.unwrap` + `Effect.sync`): the fff flag (defaulting TRUE on win32) or a native-availability probe routes to the ripgrep backend; otherwise fff. ripgrepLayer forks a full-tree index build into the layer scope at init (entries appended incrementally, directory set rebuilt per entry) and serves `find` from fuzzysort over that index while glob/grep delegate to Ripgrep.Service with results re-normalized to location-relative paths (file targets search their parent dir). fffLayer serves all three from the native engine (glob/grep prefixed by the sub-path, grep lines capped at 2000 chars, find scored then sorted by score-then-path-length); init failure logs a warning and returns an EMPTY service — search silently returns nothing rather than crashing the app.
**Invariant:** backend choice is fixed per process (no per-call dispatch); both backends return location-relative paths; fff unavailability degrades to empty results, never an error.
**Probe:** `packages/core/test/filesystem/search.test.ts` (2 it.live pin the Ripgrep.Service primitives the layer delegates to: glob array shape, grep include-filtering with submatches) + `packages/core/test/ripgrep.test.ts` (3 it.live: gitignore-aware find, `.git` excluded/`.opencode` included, surrogate-pair-safe previews). The layer-selection branch itself is source-confirmed only (flag/env-dependent).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase-memory.search_graph({ project: "opencode", query: "FileSystemSearch ripgrepLayer fffLayer Layer.unwrap fuzzysort", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt construction-time Layer.unwrap selection when a fast native path may be absent; adopt the fail-open empty-service posture ONLY for non-critical features (search results being empty is acceptable; auth being empty is not). Adapt the index-build strategy (forked full scan vs on-demand) to your workspace size. Omit the fuzzysort layer if your host has a native ranked file search.
