<!-- capsule-v2 -->
# Unified symbol extraction — screen-reject + 15-regex declaration cascade producing file activity, symbol changes, type catalog in one pass

**Source:** ext-pi-supervisor MIT `master@92c0d6df986dfd138f941001e3fcc57a3ee07247`; Codebase Memory `mnt-hdd-utopia-inspo-external-ext-pi-supervisor`. **Question:** How do you mine file paths, changed symbols, and export signatures from raw tool results in a single pass across many languages?

## One pass, three datasets
**Path/Symbol:** `src/compaction/extract/shared-symbols.ts:220-376` (`extractFileAndSymbolData`); declaration cascade :76-141 (`parseDeclName`/`parseSignature`); line iterator :149-163 (`eachLine`).
**Signature:** `extractFileAndSymbolData(blocks, tri?): { fileActivity: {read,modified,created,symbols}, typeCatalog: ExportSig[], symbolChanges: SymbolRef[] }`.
**Data Shape:** Tool sets: FILE_WRITE_TOOLS (7 names incl. snake_case), FILE_READ_TOOLS (4), FILE_CREATE_TOOLS (3 — Write-family subset). Result scans cap at **200 lines**; Edit/Write arg (`newText|new_text|content`) scans at 100.

### Decisive source
```ts
// Fast screening regex: rejects lines that can't start any declaration.
const DECL_SCREEN_RE =
  /^\s*(?:export|pub|func|def|class|type|interface|async|abstract|static|public|private|protected|struct|enum|trait|impl|module|const|fn|sealed|record|typedef|union|virtual|extern|inline)/;
```
Cascade order after screening: TS export decl → TS type → Rust decl → Rust impl → Elixir module/special/def → Java type/method → C type/func → Ruby class/def → Python def/class → Go func (**accepted only when the name starts uppercase**, :122/:136 — Go's exported-symbol rule as a filter).

**Flow:** iterate tool_calls once → classify read/write/create by name-set → write ⇒ parse symbols from new content args AND paired result via index → read ⇒ parse from result only → dedupe per file via parallel `symbolsSeen` Set map → post-pass drops Created∩Modified → catalog = modified-first then reads, 8 sigs/file, 12 files max.
**Invariant:** The screen regex must stay a strict superset of every cascade alternative or declarations get silently dropped. Dedup keys are `name@file` for refs and file-scoped name sets for activity — the same symbol read twice counts once. Signature capture skips Python privates (`def _`/`class _`).
**Probe:** `grep -c "DECL_SCREEN_RE" src/compaction/extract/shared-symbols.ts` → 2; `grep -c "m\[1\]\[0\] === m\[1\]\[0\].toUpperCase()" src/compaction/extract/shared-symbols.ts` → 1. Direct test: `tests/full-fidelity-snapshot.test.ts` normalize/filter/buildCompactionSummary suites pin pipeline outputs.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-external-ext-pi-supervisor", query: "extractFileAndSymbolData single-pass declaration regex cascade", limit: 10 });
```

## Verdict
Adopt the screen-then-cascade shape and the one-pass-three-datasets discipline for conversation mining. Adapt language regexes to your stack (drop what you don't use; keep the superset invariant). Omit the per-language arms you replace with an AST if you have real parsers available — this exists because tool output is plain text.
