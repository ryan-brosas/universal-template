<!-- capsule-v2 -->
# Export-name collection — how does automock statically enumerate a module's exports (including `export *` re-exports) WITHOUT executing it, across ESM and CJS?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How do `collectModuleExports`/`resolveModuleFormat`/`transformCode` produce the full export-name list that `automockModule` needs, and what format-resolution rules must a porter replicate?

## Static export enumeration with `export *` expansion
**Path/Symbol:** `packages/mocker/src/node/parsers.ts:collectModuleExports` (:33–124), `resolveModuleFormat` (:126–160), `transformCode` (:19–29), `initSyntaxLexers` (:9–14).
**Signature:** `collectModuleExports(filename, code, format: 'module'|'commonjs', exports=[]) => string[]`; `resolveModuleFormat(url, code) => 'module'|'commonjs'|undefined`.
**Data Shape:** uses `es-module-lexer` (ESM) and `cjs-module-lexer` (CJS) to parse WITHOUT running the module. Caches per-file export lists in `cachedFileExports` keyed by filename (and builtin module name). `transformCode` strips TS types via `module.stripTypeScriptTypes` (Node ≥22.15) so `.ts/.cts/.mts` parse cleanly.

### Decisive source
```ts
if (format === 'module') {
  const [imports_, exports_] = parseModuleSyntax(code, filename)
  const fileExports = [...exports_.map(p => p.n)]
  imports_.forEach(({ ss: start, se: end, n: name }) => {
    const substring = code.substring(start, end).replace(/ +/g, ' ')
    // `export * from 'x'` (but NOT `export * as ns`) -> resolve + read x's exports
    if (name && substring.startsWith('export *') && !substring.startsWith('export * as')) {
      fileExports.push(...tryParseModule(name))
    }
  })
  cachedFileExports.set(filename, fileExports); exports.push(...fileExports)
} else { // commonjs
  const { exports: exports_, reexports } = parseCjsSyntax(code, filename)
  const fileExports = [...exports_]
  reexports.forEach(name => fileExports.push(...tryParseModule(name)))  // CJS re-export expansion
  cachedFileExports.set(filename, fileExports); exports.push(...fileExports)
}
// parseModule(name): builtin -> Object.keys(require(name)) cached; else resolve + read + transform + recurse
function parseModule(name) {
  if (isBuiltin(name)) { /* Object.keys(getBuiltinModule(name)) cached */ }
  const resolvedModuleUrl = format === 'module' ? import.meta.resolve(name, pathToFileURL(filename).toString())
                                               : getModuleRequire().resolve(name)
  const fileContent = readFileSync(resolvedModulePath, 'utf-8')
  const code = transformCode(fileContent, resolvedModulePath)
  const resolvedModuleFormat = resolveModuleFormat(resolvedModulePath, code)
  if (ext === '.json') return ['default']
  if (resolvedModuleFormat) return collectModuleExports(resolvedModulePath, code, resolvedModuleFormat, exports)
  return []
}
return Array.from(new Set(exports))   // dedupe across all expanded sources
```

**Flow:** `collectModuleExports` parses the file's own exports, then for each `export * from`/CJS re-export recursively resolves+reads+parses the target module and splices its export names in. `resolveModuleFormat` decides ESM vs CJS by extension (`.cjs/.cts`→cjs, `.mjs/.mts`→esm), else by the nearest `package.json` `type` field, else by an ESM-syntax regex on the comment-stripped code. `transformCode` strips TS types first so lexers see valid JS. Everything is memoized in `cachedFileExports`.
**Invariant:** export enumeration is execution-free — it must never `require`/`import` the target, only lex it. `export * as ns` is deliberately NOT expanded (it's a namespace re-export, not a flat re-export) — the `startsWith('export * as')` guard is what distinguishes them. `.json` modules contribute only `default`. Builtin modules contribute `Object.keys(require(name))` (cached). The final `Set` dedupe is essential because `export *` chains can repeat names.
**Probe:** `test/unit/test/browserAutomocker.test.ts` — inline snapshots pin the exact rewritten output for `export *` and named-export forms, which depends on `collectModuleExports` producing the right names. The `resolveModuleFormat`/`transformCode` helpers are exercised transitively by every automock fixture under `test/unit/test/mocking/`.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "collectModuleExports parsers", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the execution-free lexer-based export enumeration with recursive `export *`/CJS-reexport expansion, per-file memoization, and final dedupe — a portable static-analysis contract. Adapt the resolvers (`import.meta.resolve`/`createRequire`) and the TS-strip call to your host's Node version (requires `module.stripTypeScriptTypes` ≥22.15 and `module.findPackageJSON` ≥22.14). Omit the builtin-module `Object.keys` shortcut and the `.json`→`['default']` special case unless your host matches Node's module semantics.
