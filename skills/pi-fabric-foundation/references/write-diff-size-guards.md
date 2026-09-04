<!-- capsule-v2 -->
# Write-diff size guards — when do you skip rendering a before/after diff for a write, and what makes the guard module import-safe inside a lazily-loaded dashboard?

**Source:** pi-fabric MIT `feat/veda-runner@4874ac3abefab27ee0064a3c8571ee017ceb3115`; Codebase Memory `pi-fabric`. **Question:** how do you bound diff PREVIEW work (bytes and changed-line-pair cells) independently of whether the underlying write is allowed, and why is the module dependency-free?

## Byte ceiling + changed-cell product gate in an import-isolated pure module
**Path/Symbol:** `src/providers/write-diff-limits.ts` whole file (57L): env-configured `MAX_WRITE_DIFF_BYTES` (:7-14), `MAX_WRITE_DIFF_CHANGED_LINE_CELLS` (:16-23), `writeContentForPreview` (:25-26), `shouldSkipWriteDiffBytes` (:28-35), `shouldSkipWriteDiffComplexity` (:37-57). Consumers: `src/ui/core-tool-render.ts:24` (dashboard render) + `src/providers/write-preview.ts:10` (tool wrapper). Direct tests: none standalone — behavior pinned via `tests/compaction-qa.test.ts`-style engine tests absent here; coverage caveat recorded.
**Signature:** `writeContentForPreview(content): string | undefined`; `shouldSkipWriteDiffBytes(...texts): boolean` (cumulative); `shouldSkipWriteDiffComplexity(before, after): boolean`.

### Decisive source
```ts
// Keep this module free of imports from "@earendil-works/pi-coding-agent":
// it is part of the lazily imported dashboard graph, which cannot resolve
// pi's host package in managed installs (issue #13).   ← header comment :1-5
const configuredMaxBytes = Number.parseInt(process.env.CODE_PREVIEW_MAX_WRITE_DIFF_BYTES ?? "", 10);
export const MAX_WRITE_DIFF_BYTES = Number.isFinite(configuredMaxBytes) && configuredMaxBytes > 0 ? configuredMaxBytes : 200_000;
// changed-cell product gate over trimmed common prefix/suffix LINES
let prefix = 0;
while (prefix < sharedLimit && beforeLines[prefix] === afterLines[prefix]) prefix++;
let suffix = 0; /* … symmetric suffix walk bounded by sharedLimit - prefix … */
const changedBefore = beforeLines.length - prefix - suffix;
const changedAfter  = afterLines.length  - prefix - suffix;
return changedBefore * changedAfter > MAX_WRITE_DIFF_CHANGED_LINE_CELLS;  // default 1_000_000
```

**Flow:** both limits read their env override ONCE at module load (`CODE_PREVIEW_MAX_WRITE_DIFF_BYTES`, `CODE_PREVIEW_MAX_WRITE_DIFF_CHANGED_LINE_CELLS`), accept only positive finite integers, else fall back to 200KB / 1M cells. The byte skip ACCUMULATES across all supplied texts (early-exit as soon as the running total exceeds the cap). The complexity skip walks the shared line prefix then the suffix (suffix bounded to not overlap prefix), and skips only when the PRODUCT of changed-before × changed-after line counts exceeds the cell budget — catching quadratic render cost that raw byte caps miss (two 500-line rewrites of disjoint halves = 250k cells).
**Invariant:** the guards decide only PREVIEW rendering, never the write itself — `write-preview.ts` still writes content whose preview was skipped; the module must stay import-clean of the host package because it sits on the lazy dashboard graph (issue #13 comment is the invariant's provenance); product-of-changed-sides (not sum) is what models quadratic diff-render blowups.
**Probe:** `bash -c 'cd $REFERENCE_ROOT/pi-ecosystem/pi-fabric && grep -n "200_000" src/providers/write-diff-limits.ts | wc -l'` → 1 (:14); `grep -c "MAX_WRITE_DIFF_BYTES" src/providers/write-diff-limits.ts` → 4; `grep -n "MAX_WRITE_DIFF_CHANGED_LINE_CELLS =" src/providers/write-diff-limits.ts | wc -l` → 1 (:20); `grep -c "changedBefore \* changedAfter" src/providers/write-diff-limits.ts` → 1 (:56); `grep -n "issue #13" src/providers/write-diff-limits.ts | wc -l` → 1 (:5).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "pi-fabric", query: "write preview diff limits MAX_WRITE_DIFF_BYTES skip complexity", limit: 5, fields: ["signature", "name", "file"] });
```
(Rank #1-3 resolve `shouldSkipWriteDiffComplexity` :37-57, `shouldSkipWriteDiffBytes` :28-35, `writeContentForPreview` :25-26 line-exact.)

## Verdict
Adopt cumulative byte ceilings plus changed-line-product gates as cheap pre-diff guards, and keep shared UI/provider math modules free of host-package imports when they load on lazy graphs; adapt the numeric budgets to your renderer; omit the env overrides if you have no operator-tuning surface. Coverage caveat: no dedicated upstream spec imports this module — probes are source-derived, behavior indirectly exercised via core-tool-render dashboard suites.
