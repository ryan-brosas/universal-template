<!-- capsule-v2 -->
# AGENT.md layered memory loading — in what order are instruction files discovered, how do @includes resolve, and which stripping rules keep injected context faithful?

**Source:** LocoAgent MIT `main@c01bb3f8a7b06a0db9f697c5bea485947959d226`; Codebase Memory `locoagent`. **Question:** How do you build a layered memory/instruction loader (global → user → project-tree → local) where later files outrank earlier ones, `@path` includes expand recursively without cycles, and HTML-comment/frontmatter stripping never corrupts the content the model sees?

## getMemoryFiles: priority-ordered discovery with reverse-CWD walk
**Path/Symbol:** `src/utils/agentmd.ts`:`getMemoryFiles` (`:790-1075`, memoized), `processMemoryFile` (`:618-685`), `processMdRules` (`:697-788`), `processConditionedMdRules` (`:1354-1397`).
**Signature:** `getMemoryFiles(forceIncludeExternal = false): Promise<MemoryFileInfo[]>`; `processMemoryFile(filePath, type, processedPaths, includeExternal, depth = 0, parent?): Promise<MemoryFileInfo[]>`.
**Data Shape:** `MemoryFileInfo { path, type: 'Managed'|'User'|'Project'|'Local'|'AutoMem'|'TeamMem', content, parent?, globs?: string[], contentDiffersFromDisk?, rawContent? }`.

### Decisive source
```ts
// Managed (policy) → User → Project/Local per dir from ROOT down to CWD.
// Files closer to the CWD load LAST = highest priority (model attends to latest).
let currentDir = originalCwd
while (currentDir !== parse(currentDir).root) { dirs.push(currentDir); currentDir = dirname(currentDir) }
for (const dir of dirs.reverse()) {          // root → cwd
  // nested-worktree guard: skip checked-in files from the main repo when the
  // walk passes through BOTH the worktree and its main repo (issue #29599)
  const skipProject = isNestedWorktree && pathInWorkingPath(dir, canonicalRoot) && !pathInWorkingPath(dir, gitRoot)
  if (isSettingSourceEnabled('projectSettings') && !skipProject) {
    // AGENT.md, .claude/AGENT.md, .claude/rules/*.md — then AGENT.local.md
```

**Flow:** Managed file+rules always → User file+rules (if user settings enabled; User may always include external files) → every dir from filesystem root down to original CWD loads Project memory + `.claude/rules/*.md`, then Local (`AGENT.local.md`) → AutoMem/TeamMem entrypoints last → one shared `processedPaths` set dedupes across ALL layers → result wrapped by `getAgentMds` into "Contents of <path>" blocks under a single OVERRIDE-instruction banner.
**Invariant:** Priority comes purely from ORDER (later entries win attention), so the root→CWD direction is not cosmetic — reversing it silently inverts precedence. The shared `processedPaths` Set spans layers: a file included once anywhere is never loaded twice. In a git worktree nested inside its main repo, checked-in Project files above the worktree are SKIPPED (the worktree has its own checkout) while gitignored `AGENT.local.md` still loads from the main repo. `getMemoryFiles` is memoized; `clearMemoryFileCaches()` invalidates for correctness WITHOUT firing hooks, `resetGetMemoryFilesCache(reason)` is reserved for real reloads (compaction) so the InstructionsLoaded hook reports honestly (:1093-1130).
**Probe:** No upstream test executes on this host (coverage caveat — Bun-run suite). Deterministic probe: `search_graph --project locoagent --name-pattern "^processMemoryFile$"` resolves `locoagent.src.utils.agentmd.processMemoryFile`; the doc header (:1-26) pins discovery order and include semantics as normative comments.

## @include extraction on lexed tokens
**Path/Symbol:** `src/utils/agentmd.ts`:`extractIncludePathsFromTokens` (`:451-535`), `MAX_INCLUDE_DEPTH = 5` (`:537`).
**Signature:** `extractIncludePathsFromTokens(tokens, basePath): string[]`.
**Data Shape:** Accepts `@path`, `@./rel`, `@~/home`, `/abs`; fragment suffix `#section` stripped; `\ ` unescaped to literal space; resolved against `dirname(basePath)`.

### Decisive source
```ts
const includeRegex = /(?:^|\s)@((?:[^\s\\]|\\ )+)/g
...
// code / codespan tokens are skipped entirely — @paths inside fenced code
// blocks or inline code NEVER resolve:
if (element.type === 'code' || element.type === 'codespan') continue
```

**Flow:** ONE marked `Lexer({ gfm: false })` pass serves both comment-stripping and include extraction (single lex invariant) → recurse tokens collecting text nodes only → validate path shape (`./`, `~/`, absolute, or `[a-zA-Z0-9._-]` start; rejects `@self`, `%`, heading anchors) → dedupe via Set → caller re-enters `processMemoryFile` per include with `depth + 1` until MAX_INCLUDE_DEPTH=5; `processedPaths` breaks cycles; missing files return empty silently; includes render BEFORE the including file but the parent link records provenance.
**Invariant:** Include resolution must run on PRE-strip tokens but must ignore html-token interiors except comment RESIDUE (so `<!-- note --> @./file.md` still resolves — residue extracted after removing `<!-- ... -->` spans). gfm:false is REQUIRED: with GFM on, `~/path` tokenizes as strikethrough and vanishes. Depth cap + visited-set together make hostile include graphs terminate.
**Probe:** Coverage caveat: no runnable test host. Deterministic probe: grep pins the regex and code-skip at `src/utils/agentmd.ts:459` and `:496-498`; `MAX_INCLUDE_DEPTH` at `:537`.

## Faithful-content stripping (comments, frontmatter, truncation)
**Path/Symbol:** `src/utils/agentmd.ts`:`stripHtmlComments` (`:292-334`), `parseFrontmatterPaths` (`:254-279`), `parseMemoryFileContent` (`:343-400`), `TEXT_FILE_EXTENSIONS` (`:96-227`).
**Signature:** `stripHtmlComments(content): { content, stripped }`.
**Data Shape:** `contentDiffersFromDisk=true` ⇒ `rawContent` carries untouched disk bytes so callers can cache an `isPartialView` entry (presence dedups, but Edit/Write still demand a fresh Read).

### Decisive source
```ts
// Only rebuild via tokens when a comment actually needs stripping —
// marked normalises \r\n during lex, so round-tripping a CRLF file
// through token.raw would spuriously flip contentDiffersFromDisk.
const hasComment = withoutFrontmatter.includes('<!--')
const tokens = hasComment || includeBasePath !== undefined ? new Lexer({ gfm:false }).lex(withoutFrontmatter) : undefined
const strippedContent = hasComment && tokens ? stripHtmlCommentsFromTokens(tokens).content : withoutFrontmatter
```
and inside the stripper: unclosed `<!--` with no `-->` is LEFT IN PLACE ("so a typo doesn't silently swallow the rest of the file"); html-block residue after `-->` on the same line is preserved.

**Flow:** extension gate first (non-text extensions never enter memory — binary-safe) → frontmatter parsed out, `paths:` globs kept (trailing `/**` trimmed because the ignore library treats a path as matching itself plus contents; all-`**` ⇒ no globs) → conditional strip → AutoMem/TeamMem entrypoints truncated to line+byte caps → diff-vs-disk recorded with raw backup.
**Invariant:** Stripping is BLOCK-level only (CommonMark html blocks): inline comments inside paragraphs, anything in code spans/fences survive verbatim. The CRLF round-trip trap is the decisive subtlety — lexing normalizes line endings, so you must NOT rebuild content through tokens unless a strip actually has to happen, otherwise every CRLF file would be flagged modified. Unclosed comments fail visible rather than eating the document.
**Probe:** Coverage caveat: no runnable test host; `agentmd.ts` is parse_partial at :730 (constructs near that line may be absent from graph — cited symbols confirmed via search_graph + direct read). Deterministic probe: grep pins the CRLF comment at `src/utils/agentmd.ts:368-370` and the unclosed-comment rule at `:289-291`.

## Conditional rules matched per target path
**Path/Symbol:** `src/utils/agentmd.ts`:`processConditionedMdRules` (`:1354-1397`), `getMemoryFilesForNestedDirectory` (`:1249-1318`).
**Data Shape:** Rule frontmatter `paths: [glob...]`; Project rules' globs are relative to the dir CONTAINING `.claude`; Managed/User rules relative to original CWD.

### Decisive source
```ts
const baseDir = type === 'Project'
  ? dirname(dirname(rulesDir))        // parent of .claude
  : getOriginalCwd()
const relativePath = isAbsolute(targetPath) ? relative(baseDir, targetPath) : targetPath
// ignore() throws on empty strings, ../ escapes, and absolute relatives —
// such paths can't match baseDir-relative globs anyway:
if (!relativePath || relativePath.startsWith('..') || isAbsolute(relativePath)) return false
return ignore().add(file.globs).ignores(relativePath)
```

**Flow:** eager pass loads UNconditional rules; when the agent touches a file in a nested dir, `getMemoryFilesForNestedDirectory` lazily loads that dir's AGENT.md + unconditional rules with a CLONED processedPaths set (conditional files must stay unmarked) then filters conditional rules by target-path globs; the clone is merged back afterwards.
**Invariant:** Two-phase loading exists so conditional rules fire ONLY for matching paths; the cloned-set dance prevents a conditional rule seen in dir A from being silently skipped in dir B. Paths escaping the base (`../`) are excluded BEFORE calling `ignore()` because the library throws on them — filtering first is correctness, not style.
**Probe:** Coverage caveat: no runnable test host. Deterministic probe: `search_graph --project locoagent --name-pattern "^processConditionedMdRules$"` resolves it; grep pins `dirname(dirname(rulesDir))` at `src/utils/agentmd.ts:1379`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "locoagent", query: "getMemoryFiles processMemoryFile stripHtmlComments include", limit: 10, fields: ["signature", "file"] });
```

## Verdict
Adopt order-as-priority layered discovery, token-gated include extraction with depth+cycle guards, block-only comment stripping with the CRLF no-round-trip rule, rawContent preservation for transformed views, and base-dir-scoped conditional rule matching. Adapt file names (AGENT.md vs your marker), layer labels, and truncation caps to your product. Omit the analytics/hook/feature-flag plumbing unless your host has the same hook surface; keep the clear-vs-reset cache distinction whenever a memoized loader fires side effects.
