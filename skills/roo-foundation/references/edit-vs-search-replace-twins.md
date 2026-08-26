<!-- capsule-v2 -->
# edit vs search_replace twin divergence — same-looking string replacement, opposite $-pattern semantics

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** Roo ships `edit` AND `search_replace` tools with near-identical bodies — which behavioral differences must a porter preserve or consciously collapse?

## Two tool classes, three real divergences
**Path/Symbol:** `src/core/tools/EditTool.ts:EditTool.execute` (lines 28–244; alias `searchAndReplaceTool = editTool` :279) vs `src/core/tools/SearchReplaceTool.ts:SearchReplaceTool.execute` (no replace_all param).
**Signature:** edit: `{file_path, old_string, new_string, replace_all?}`; search_replace: `{file_path, old_string, new_string}` (3 params only).
**Data Shape:** both normalize `\r\n→\n` in file content AND both needle strings before matching; both count matches via `content.split(old).length - 1`.

### Decisive source
```ts
// EditTool — literal replacement (callback form defeats $-pattern interpretation)
newContent = fileContent.replace(normalizedOld, () => normalizedNew)
…
// SearchReplaceTool — plain string arg: '$&', '$1' etc. in new_string ARE interpreted
const newContent = fileContent.replace(normalizedOldString, normalizedNewString)
```

**Flow (shared):** validate required params → reject `old === new` ("are identical. No changes needed.") → rooIgnore gate → file-exists → read+normalize CRLF → matchCount via split → no-match error (`recordToolError(name, "no_match")`) → apply → diff view/approval/save ladder identical to ApplyPatchTool's per-file flow.
**Invariant:** THREE divergences a porter must know: (1) `$&`-injection — edit's callback form makes new_string LITERAL, search_replace's direct form lets `$&`/`$1` splice matched text (a live footgun when models emit literal dollar patterns); (2) multi-match policy — edit offers `replace_all:true` to replace every occurrence (regex built via private `escapeRegExp`, still literal), otherwise rejects N>1; search_replace ALWAYS rejects N>1 ("This tool can only replace ONE occurrence at a time") and records `"multiple_matches"`; (3) path handling — search_replace accepts absolute file_path (`path.isAbsolute → path.relative(cwd)`), edit treats it as relative only. EditTool additionally exports the legacy alias `searchAndReplaceTool = editTool` for backward compat.
**Probe:** `grep -c '() => normalizedNew' src/core/tools/EditTool.ts` → 2; `grep -cF 'replace(normalizedOldString, normalizedNewString)' src/core/tools/SearchReplaceTool.ts` → 1; `grep -cF 'This tool can only replace ONE occurrence at a time' src/core/tools/SearchReplaceTool.ts` → 1; `grep -cF "Found \${matchCount} matches of 'old_string'" src/core/tools/EditTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "Roo-Code", query: "EditTool SearchReplaceTool old_string matchCount", limit: 10 });
```

## Verdict
Adopt BOTH behaviors if you keep two tools (literal edit + pattern-interpreting search_replace is the upstream contract); if you collapse them, pick the LITERAL form and document the loss. Adapt error copy freely. Direct tests: `src/core/tools/__tests__/editTool.spec.ts`, `searchReplaceTool.spec.ts` (describe "searchReplaceTool" :72; parameter-validation/file-access/logic describes :213/:251/:267 incl "returns error when multiple matches are found" :280, "allows empty new_string for deletion" :229), plus `searchAndReplaceTool.spec.ts` pinning the alias.
