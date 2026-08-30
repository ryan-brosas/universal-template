<!-- capsule-v2 -->
# list_files presentation kernel — why does the tool re-resolve every path before checking .rooignore, and how are hidden/protected entries marked?

**Source:** Roo-Code Apache-2.0 `main@b867ec9145750d0ae1ff7f02d35406e9bf2a0b16`; Codebase Memory `Roo-Code`. **Question:** How does a 200-entry-capped recursive listing stay navigable for a model while still honoring ignore and write-protection rules?

## formatFilesList — sort, re-resolve, mark, truncate-notice
**Path/Symbol:** `src/core/prompts/responses.ts:formatFilesList` (117–191); caller `src/core/tools/ListFilesTool.ts:execute` (22–69).
**Signature:** `formatFilesList(absolutePath: string, files: string[], didHitLimit: boolean, rooIgnoreController: RooIgnoreController | undefined, showRooIgnoredFiles: boolean, rooProtectedController?: RooProtectedController): string`.
**Data Shape:** input files are ABSOLUTE paths from `listFiles(absolutePath, recursive || false, 200)`; output is one plain-text string consumed by BOTH the model (pushToolResult) and the UI ask envelope.

### Decisive source
```ts
// path is relative to absolute path, not cwd
// validateAccess expects either path relative to cwd or absolute path
// otherwise, for validating against ignore patterns like "assets/icons", we would end up with just "icons", which would result in the path not being ignored.
const absoluteFilePath = path.resolve(absolutePath, filePath)
const isIgnored = !rooIgnoreController.validateAccess(absoluteFilePath)

if (isIgnored) {
    // If file is ignored and we're not showing ignored files, skip it
    if (!showRooIgnoredFiles) { continue }
    // Otherwise, mark it with a lock symbol
    rooIgnoreParsed.push(LOCK_TEXT_SYMBOL + " " + filePath)
} else {
    const isWriteProtected = rooProtectedController?.isWriteProtected(absoluteFilePath) || false
    if (isWriteProtected) { rooIgnoreParsed.push("🛡️ " + filePath) }
    else { rooIgnoreParsed.push(filePath) }
}
```

**Flow:** map to paths relative to the LISTED directory (`path.relative(absolutePath, file).toPosix()`, trailing `/` preserved for dirs) → segment-wise sort: at the FIRST differing segment a directory sorts before files, else localeCompare(numeric, sensitivity:"base"), prefix-equal shorter first → optional rooignore/write-protect pass above → join `\n`; `didHitLimit` appends `(File list truncated. Use list_files on specific subdirectories if you need to explore further.)`; empty or single-empty-string renders `No files found.`
**Invariant:** (1) The RE-RESOLVE before validateAccess is load-bearing: relative-only names would strip parent segments and nested ignore patterns like `assets/icons` would silently stop matching — validateAccess must receive cwd-relative or absolute paths (matches the realpath-before-match rule mined in rooignore-access-control). (2) Ignored-but-visible entries get LOCK_TEXT_SYMBOL prefix; write-protected get 🛡️ — VISIBILITY markers are how the model learns a path exists but is gated, vs omission which teaches nothing. (3) The dirs-first segment sort guarantees truncated listings still reveal explorable directories (stated intent in source comment). (4) The 200-entry cap lives in the TOOL call (`listFiles(..., 200)`), not in formatFilesList — reuse the formatter with any cap. (5) SearchFilesTool passes `task.rooIgnoreController` straight into regexSearchFiles instead: transport-side filtering that consumes result budget (see ripgrep-search-transport); the two tools deliberately split filtering location.
**Probe:** runner BLOCKED (no direct spec for responses.formatFilesList at pin). Deterministic source pins from repo root: `grep -c 'Use list_files on specific subdirectories' src/core/prompts/responses.ts` → 1; `grep -c 'LOCK_TEXT_SYMBOL + " " + filePath' src/core/prompts/responses.ts` → 1; `grep -c 'listFiles(absolutePath, recursive || false, 200)' src/core/tools/ListFilesTool.ts` → 1.
**Retrieve:**
```ts
await mcp.codebase_memory.get_code_snippet({ project: "Roo-Code", qualified_name: "Roo-Code.src.core.prompts.responses.formatFilesList" });
```

## Verdict
Adopt re-resolve-before-validate, marker-symbol visibility for gated entries, and the truncation notice that names the recovery command. Adapt marker glyphs and cap values. Omit the Cline-era naming; keep the pure-function shape (controller objects passed in, no I/O). Coverage caveat: no direct spec at pin — pinned via source read + byte-exact greps; ListFilesTool wrapper itself is spec-free by design (thin).
