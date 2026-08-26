<!-- capsule-v2 -->
# Import resolution ladders — how do four languages' import syntaxes resolve to repo files without false edges?

**Source:** pi-fovea MIT `DETACHED@217a103`; Codebase Memory `pi-fovea`. **Question:** Go imports are full module paths, Rust has `crate::`/mod.rs trees, TS imports "./x.js" pointing at .ts sources, Python uses dotted modules — what resolution rules produce high-precision FILE-level import edges at monorepo scale?

## Suffix-indexed per-family resolvers with uniqueness gates
**Path/Symbol:** `src/core/build.ts:buildImportIndex/resolveImportToFile/langFamily/CODE_EXTS_BY_LANGFAMILY` (:744-869); patterns `src/core/extract.ts:IMPORT_PATTERNS` (:287-306).
**Signature:** `buildImportIndex(files): ImportIndex {fileSet, filesByDir, goDirsBySuffix, rsByBase, tsByTailStem}`; `resolveImportToFile(spec, fromFile, index): string | undefined`.
**Data Shape:** Precomputed suffix indexes replace O(imports × files) scans ("quadratic-blows on big trees"): Go last-k-segment dir suffixes k≤3; Rust module basename → `foo.rs`/`foo/mod.rs`; TS last path segment → `x.ts`/`x/index.ts`.

### Decisive source
```ts
if (spec.startsWith("./") || spec.startsWith("../")) {
  let base = posix.normalize(posix.join(posix.dirname(fromFile), spec));
  // NodeNext convention: TS files import "./sibling.js" — the .js refers to
  // the .ts source. Strip a runtime extension before probing.
  base = base.replace(/\.(?:[cm]?js|jsx)$/, "");
  for (const ext of CODE_EXTS_BY_LANGFAMILY[fam] ?? []) {
    if (fileSet.has(base + ext)) return base + ext;
    if (fileSet.has(`${base}/index${ext}`)) return `${base}/index${ext}`;
  }
}
if (fam === "go") {   // match by LAST 1-3 path segments against indexed dirs;
  const matches = (index.goDirsBySuffix.get(suffix) ?? [])
    .filter((d) => d === suffix || d.endsWith(`/${suffix}`));
  if (matches.length === 1) { /* only an unambiguous dir resolves */ }
}
if (fam === "rs") {
  const modPath = spec.replace(/^crate::|^self::/, "").replace(/::/g, "/");
  for (const cand of [`src/${modPath}.rs`, `${modPath}.rs`]) if (fileSet.has(cand)) return cand;
  // basename fallback requires EXACTLY ONE hit among foo.rs / x/foo.rs / x/foo/mod.rs
}
```

**Flow:** extract import sites via per-language ast-grep pattern sets (TS export-from decomposed into named+star forms after ast-grep rejected `export $$$I from` parse-wide; Go import BLOCKS have quoted specs pulled from captured block text) → resolve to files per family ladder → emit file-level `imports` edges at w=0.3 (the low-conductance backbone) → test files additionally wire `tests` edges (w=0.6) to their imported targets. Call edges then resolve callee NAMES using those imported-file sets: same-file defs first, then imported files, then globally unique defs, with conductance decaying by definition cardinality (≤8 defs→0.7, ≤24→0.45, else 0.25; >48 candidates skipped entirely — "a name defined 40 times is ambient noise").
**Invariant:** Ambiguity refuses to resolve (single-hit gates everywhere) — a wrong edge corrupts diffusion worse than a missing one. The NodeNext .js→.ts strip is load-bearing for TS repos; CALL_WARDS (loggers, test frameworks, language builtins) are excluded AT EXTRACTION so mega-hubs never form.
**Probe:** `tests/extract.test.ts` — "extracts imports across languages" (./types, ./api, Go module path, Python os); `tests/report.test.ts` umbrella-boundary fixtures; `tests/ops.test.ts` "explains direct call relationships before the thermal periphery".

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-pi-fovea", query: "resolveImportToFile buildImportIndex tsByTailStem", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt family-split resolution with suffix indexes, uniqueness-gated ambiguity refusal, the NodeNext strip, cardinality-decayed call weights, and builtin/test-framework call wards. Adapt extension tables and ward lists to your language set. Omit the outline text-format fallback details unless targeting pre-structured-outline ast-grep versions.
