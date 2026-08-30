<!-- capsule-v2 -->
# Autocomplete trigger discipline — when may a suggestion popup appear, and how does completion feel native?

**Source:** pi-upstream MIT `main@534bcbffb7e1e7551d9ee3572dfeb278e203e493`; Codebase Memory `pi-upstream`. **Question:** A porter's autocomplete ambushes users writing prose — what separates polite triggers from forced ones, and how is quoting handled?

## Natural triggers only for path-shaped prefixes; Tab force-completes anything
**Path/Symbol:** `packages/tui/src/autocomplete.ts` (786L; tree-walk gating :141-160, base-dir statSync :541, re-stat :622).
**Signature:** three domains — slash commands (line-start `/`), @-attachments (token-start `@`, optionally quoted), paths (natural only when the prefix looks like a path: contains `/`, starts `.` or `~/`, or empty-after-space).
**Data Shape:** Quote-awareness runs through the whole stack: an unclosed quote REDEFINES the current token; completed values re-quote when they contain spaces; applyCompletion drops one quote in the triple edge (quoted prefix + value ending in quote + quote already after cursor).

### Decisive source
```ts
args.push("--full-path");   // ONLY when the query contains a slash
// ...
if (!statSync(baseDir).isDirectory()) { /* refuse before spawning fd */ }
```
Tree walk is external (`fd`, respects .gitignore, `.git` excluded by flag AND result filter, SIGKILL-on-abort); directory completions add NO trailing space (cursor backed up one when quoted) so the user keeps drilling; FILE completions add the terminating space — continuation vs termination is encoded in the suffix choice. Slash application inserts `/name ` with cursor advanced +2.

**Flow:** keystroke → classify token under cursor per domain → natural trigger only if path-shaped → async suggestion request serialized by the editor's monotonic startToken (editor capsule) → apply with domain-specific quote/space math.
**Invariant:** Users are never ambushed mid-prose: without an explicit force (Tab) or a path-shaped prefix, no popup. Suggestions must always read as continuations of what's on screen (full-path display when the query has a slash; verified base dir before spawning).
**Probe:** `packages/tui/test/autocomplete.test.ts` (trigger + quote-math cases).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-upstream", query: "autocomplete naturalTrigger statSync full-path", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt natural-vs-forced trigger separation, quote-aware token math, and suffix-encoded continuation. Adapt domains to your command grammar. Omit the external fd dependency if your host bundles a walker. Coverage caveat: none.
