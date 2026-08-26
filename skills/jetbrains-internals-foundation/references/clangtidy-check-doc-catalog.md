<!-- capsule-v2 -->
# clangtidy-check-doc-catalog — where does per-linter-check documentation live so the UI never needs the network?

**Source:** JetBrains CLion installed build `2026.2.1@262.9437.136` (`plugins/cidr-clangd/docs/clangTidyDoc/`); Codebase Memory `jetbrains-clion`. **Question:** How do you ship documentation for ~600 third-party tool checks such that hovering a check id resolves instantly and offline?

## Filename-keyed check catalog
**Path/Symbol:** `plugins/cidr-clangd/docs/clangTidyDoc/<module-dir>/<check-suffix>.html` — 595 HTML files over 25 module dirs (abseil, bugprone, cert, clang-analyzer, concurrency, cppcoreguidelines, fuchsia, google, hicpp, linuxkernel, llvm, llvmlibc, misc, modernize, mpi, objc, openmp, performance, portability, readability, zircon, altera, android, boost, darwin).
**Data Shape:** filename stem IS the check suffix (`modernize/use-using.html` ↔ check id `modernize-use-using`); `<title>` carries the full id ("clang-tidy - modernize-use-using"); pages are upstream Sphinx output with ONE deliberate post-processing marker.

### Decisive source
```html
<!-- head -12 modernize/use-using.html (direct read) -->
<html>
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>clang-tidy - modernize-use-using</title>
	/* CLION CLANG-TIDY DOCUMENTATION CSS PLACEHOLDER */
  </head>
```

**Flow:** build pipeline downloads/mirrors upstream clang-tidy docs → rewrites the CSS link into the PLACEHOLDER comment (IDE injects its own stylesheet at render time) → UI resolves a check id by splitting module prefix + loading `<module>/<suffix>.html`.
**Invariant:** the catalog is DATA, keyed by convention (dir = module, file = check); the placeholder comment is the integration seam — upstream doc structure is otherwise untouched; graph File census counts 598 paths here because shared assets (basic.css, list.html) sit beside the 595 checks — name your slice before citing counts.
**Probe:** executed byte-exact pre-write: `find . -name '*.html' | wc -l` → `595`; `find -mindepth 1 -maxdepth 1 -type d | wc -l` → `25`; `grep -l "CLION CLANG-TIDY DOCUMENTATION CSS PLACEHOLDER" modernize/*.html` → avoid-bind.html, avoid-c-arrays.html.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.query_graph({ project: "jetbrains-clion", query: "MATCH (f:File) WHERE f.file_path STARTS WITH 'plugins/cidr-clangd/docs/clangTidyDoc' RETURN count(f) AS tidy_docs", max_rows: 5 });
```
(executed live this pass → tidy_docs = 598 incl. shared assets.)

## Verdict
Adopt filename-convention catalogs + stylesheet-placeholder rewriting for bundling third-party docs; adapt the key scheme to your id grammar; omit Sphinx specifics. Same method family as inspection-description-catalog (rule docs keyed by short name).