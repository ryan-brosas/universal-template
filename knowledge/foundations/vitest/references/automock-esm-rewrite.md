<!-- capsule-v2 -->
# Automock ESM rewrite — how is a module's source statically rewritten so every export becomes a mocked binding WITHOUT executing the original module?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`). **Question:** How does `automockModule` transform exports/imports into a self-mocking module, and why does `export *` force the special re-export expansion path?

## automockModule export surgery
**Path/Symbol:** `packages/mocker/src/node/automock.ts:automockModule` (:17–214) — ExportAllDeclaration expansion (:41–75), named-export handling (:77–180), default rewrite (:181–186), appended module object (:189–213).
**Signature:** `function automockModule(code: string, mockType: 'automock' | 'autospy', parse: (code: string) => any, options?: { globalThisAccessor?, id? }): MagicString`.
**Data Shape:** collects `allSpecifiers: { name, alias? }[]`; defers graph-dependent work into `replacers: (() => void)[]` executed AFTER the AST walk; emits appended code defining `__vitest_current_es_module__`, `__vitest_mocked_module__ = globalThis["__vitest_mocker__"].mockObject(moduleObject, "<type>")`, per-specifier consts, and a final `export {}`.

### Decisive source
```ts
// export * cannot be statically enumerated from THIS module — resolve + READ
// the target at transform time and inline its export names as explicit imports
const moduleUrl = import.meta.resolve(source, pathToFileURL(options.id).toString())
const moduleContent = readFileSync(modulePath, 'utf-8')
const transformedCode = transformCode(moduleContent, moduleUrl)
const moduleFormat = resolveModuleFormat(moduleUrl, transformedCode)
const moduleExports = collectModuleExports(modulePath, transformedCode, moduleFormat || 'module')
replacers.push(() => { /* overwrite node with `import { e1, e2 } from 'source'` */ })
// no options.id (browser): loud refusal instead of wrong mock
if (!options.id) throw new Error(`automocking files with \`export *\` is not supported ...`)

// `export const x = 1` → strip ONLY the `export` keyword, keep the declaration alive
m.remove(node.start, (declaration as Positioned<Declaration>).start)

// `export { a as b } from 'mod'` → rename locals to collision-proof temp names,
// remember the alias, replace node with an import of the same source
const importedName = `__vitest_imported_${importIndex++}__`
...
m.overwrite(node.start, node.end, importString)

// `export default expr` → `const __vitest_default = expr`
m.overwrite(node.start, declaration.start, `const __vitest_default = `)

// tail: build the mocked namespace + re-export mocked bindings under ORIGINAL names
const __vitest_current_es_module__ = {
  __esModule: true,
  ${allSpecifiers.map(({ name }) => `["${name}"]: ${name},`).join('\n  ')}
}
const __vitest_mocked_module__ = globalThis["__vitest_mocker__"].mockObject(__vitest_current_es_module__, "automock")
const __vitest_mocked_0__ = __vitest_mocked_module__["test"]
export {
  __vitest_mocked_0__ as test,
}
```

**Flow:** parse once → walk top-level statements collecting specifier names while REWRITING each export form in place (`export` keyword stripped for local declarations; re-exports become imports with temp names; default becomes a const) → run deferred `export *` replacers (which may ADD specifiers) → append the module-object + mockObject + aliased re-export block. The consuming runtime (`globalThis.__vitest_mocker__.mockObject`) turns every value into automock spies/spies per `mockType`.
**Invariant:** the original declarations stay but are NEVER exported under their own names — only the final `export { mocked as name }` block defines the public surface, which is what makes automock execution-free. Specifier collection MUST complete before replacers run (`replacers.forEach(cb => cb())` after the loop) because `export *` names dedupe against already-seen names/aliases. The `options.id` guard is the portability seam: browser transforms have no FS access to expand `export *` and must fail loudly rather than emit a partial mock.
**Probe:** `test/unit/test/browserAutomocker.test.ts` — inline-snapshot pins the exact emitted output for function/class/default/export-list forms (:13–24 shows the full expected rewrite for `export function test() {}`).
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "automockModule", limit: 5, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the collect-then-rewrite order and execution-free mocked-re-export shape for static mock transforms over ESM. Adapt the parser injection (`parse`) and resolver (`import.meta.resolve` + fs read) to your transform host. Omit `export *` support (keep the loud error) unless your host can resolve+read dependency sources at transform time.
