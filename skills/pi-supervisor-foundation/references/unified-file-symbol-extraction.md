<!-- capsule-v2 -->
# Unified file/symbol extraction — how do file activity, symbol changes, and a type catalog come out of ONE pass?

**Source:** pi-supervisor MIT `master@92c0d6d`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** What classification sets decide read/modified/created, and which dedup rules keep the three outputs consistent?

## extractFileAndSymbolData (`src/compaction/extract/shared-symbols.ts`)
**Path/Symbol:** `src/compaction/extract/shared-symbols.ts:extractFileAndSymbolData` (:220-376); declaration regex cascade `parseDeclName` (:76-124); fast screen `DECL_SCREEN_RE` (:73-74); `parseSignature` (:126-141).
**Signature:** `extractFileAndSymbolData(blocks, tri?): UnifiedExtractResult` = `{fileActivity{read,modified,created,symbols}, typeCatalog: ExportSig[], symbolChanges: SymbolRef[]}`.
**Data Shape:** FILE_WRITE_TOOLS={Edit,Write,edit,write,edit_file,write_file,MultiEdit}; FILE_READ_TOOLS={Read,read,read_file,View}; FILE_CREATE_TOOLS⊂WRITE={Write,write,write_file}.

### Decisive source
```ts
// Replaces the triple-redundant scan performed by extractFiles() (200-line),
// extractSymbolChanges() (300-line), extractTypeCatalog() (150-line) — all
// scanning the same tool_result content with overlapping regex patterns.
if (isWrite) {
  const newText = b.args.newText ?? b.args.new_text ?? b.args.content ?? '';
  const syms = extractSymbolsFromText(newText, 100, true);   // symbols from EDIT PAYLOADS
}
if (isRead || isWrite) {
  const r = tri.get(i);                                       // shared look-ahead result
  if (r && r.text && !r.isError) {
    const syms = extractSymbolsFromText(resultText, 200, true);
    ...
  }
}
// Dedup + ordering:
for (const p of modified) created.delete(p);                  // Write-after-Write ⇒ not "created"
const typeCatalog = [...modifiedSigs, ...readSigs].slice(0, 12);  // modified FIRST, cap 12 files × 8 sigs
```

**Flow:** single pass over tool_calls → path via `extractPath` (path/file_path/filePath/file key ladder) → classify into read/modified/created sets → symbols harvested from BOTH edit payloads (newText aliases, 100 lines) AND paired non-error results (200 lines) → per-file signature lists with modified-flag → symbol refs keyed `name@file` for dedup. Language cascade order: TS export decl → TS type → Rust fn/impl → Elixir module/special/def → Java type/method → C type/func → Ruby class/def → Python def/class → Go func (EXPORT-ONLY: Go requires uppercase first rune; Python skips `_`-private signatures).
**Invariant:** (1) Created ⊆ Modified always enforced by deletion AFTER collection — checking order matters. (2) Error results contribute NOTHING (skipped before parsing). (3) The catalog is modified-first so the judge sees what CHANGED before what was merely read. (4) `DECL_SCREEN_RE` quick-reject means lines not STARTING with a declaration keyword never hit the 15-regex cascade — porters adding languages must extend the screen too or lose performance.
**Probe:** `tests/full-fidelity-snapshot.test.ts` structured-sections suite (:143-160); regex cascade pinned at `shared-symbols.ts:21-53`; graph pin resolves `extractFileAndSymbolData` at `src/compaction/extract/shared-symbols.ts`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractFileAndSymbolData DECL_SCREEN_RE typeCatalog modifiedSigs", limit: 8 });
```

## Verdict
Adopt single-pass three-output extraction + created⊆modified + modified-first catalog ordering. Adapt tool-name sets and add language regexes for your stack (update DECL_SCREEN_RE in lockstep). Omit exotic-language arms you don't need — the screen makes removal safe.
