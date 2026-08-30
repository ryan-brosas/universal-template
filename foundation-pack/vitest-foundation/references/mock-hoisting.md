<!-- capsule-v2 -->
# vi.mock hoisting transform — how does a source-level AST transform make `vi.mock`/`vi.hoisted` calls execute before static imports?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** How do you rewrite an ESM module so mock registrations and hoisted factories run before every import — without executing user code at transform time?

## `hoistMocks` MagicString transform
**Path/Symbol:** `packages/mocker/src/node/hoistMocks.ts:hoistMocks` (93–590) — fast-path regex (82–84), `defineImport` (142–160), `onCallExpression` visitor (319–426), nesting validation (480–494), top-level validation (496–528), hoist moves (530–570), synthetic import repair (572–587); driven by `hoistMocksPlugin.ts` (`transform` filter + `post` hook).
**Signature:** `function hoistMocks(code: string, id: string, parse: (code: string) => any, options?: HoistMocksOptions): MagicString | undefined`.
**Data Shape:** returns a mutated MagicString or `undefined` when no hoistable call exists; options rename the matched methods (`utilsObjectNames ['vi','vitest']`, hoistable/dynamic-import/hoisted method lists, `hoistedModule = 'vitest'`).

### Decisive source
```ts
// this is a fork of Vite SSR transform
const regexpHoistable = /\b(?:vi|vitest)\s*\.\s*(?:mock|unmock|hoisted|doMock|doUnmock)\s*\(/
...
// 1. record imports as binding -> "__vi_import_N__.name" map
// 2. esmWalker visitors:
onIdentifier(id, info, parentStack) {   // rebind imported identifiers to the hoisted dynamic import vars
  if (info.hasBindingShortcut) s.appendLeft(id.end, `: ${binding}`)
  else if (info.classDeclaration) { s.prependRight(topNode.start, `const ${id.name} = ${binding};\n`) }
  else if (!info.classExpression) s.update(id.start, id.end, binding)
}
onCallExpression(node) {
  ...assertNotDefaultExport / assertNotNamedExport('Cannot export the result of "vi.mock"...')
  if (moduleInfo.type === 'ImportExpression') {   // vi.mock(import('./x')) -> vi.mock('./x')
    s.overwrite(moduleInfo.start, moduleInfo.end, s.slice(source.start, source.end))
  }
}
// 3. validate no hoisted node is nested inside another:
if (node.start >= otherNode.start && node.end <= otherNode.end) throw createError(otherNode, node)
// 4. validate all are top-level (unless import.meta.vitest), with sourcemap-mapped positions in the error
// 5. move nodes: s.move(node.start, end, hoistIndex) after the hashbang
// 6. imports become `const __vi_import_N__ = await import("src")` moved AFTER all mocks
```

**Flow:** cheap regex prefilter (skips files/comments/strings-only mentions) → parse → collect imports into `__vi_import_N__` ids → walk AST rebinding imported identifiers so references resolve through the dynamic imports → detect `vi.mock/unmock/hoisted/doMock/doUnmock`, rewriting `vi.mock(import('x'))` to string form → validate (no export-of-result, no nested hoisted calls, top-level only with precise code-frame + original-position errors) → `s.move` mock/hoisted nodes above everything, then move converted imports below them.

**Invariant:** (1) transform is purely textual (MagicString) preserving sourcemaps — never evaluates user code; (2) ALL imports become awaited dynamic imports ordered AFTER mock registrations — that ordering is the whole feature; (3) nested hoisted calls (e.g. inside `test()`) are a loud error explaining they'd actually run first; `import.meta.vitest` in-source tests are exempt from the top-level check; (4) missing-but-used `vi` is auto-imported, or a runtime check throws "import the mocks API directly from 'vitest'".

**Probe:** `test/unit/test/injector-mock.test.ts` — :33 hoists mock/unmock/hoisted; :46 vitest import always hoisted first; :78 imports become awaited dynamic imports under mocks; :1620 seven nested calls produce the "defined outside of the module's top level scope" error with mapped positions; :1699 `import.meta.vitest` exemption; :1718/:1726 no transform when API appears only in comments/strings.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "hoistMocks esmWalker hoistedNodes defineImport", limit: 10, fields: ["signature", "name", "file"] });
// resolves: vitest.packages.mocker.src.node.hoistMocks.hoistMocks (+ HoistMocksOptions)
```

## Verdict
Adopt the regex-prefilter + MagicString-reorder approach for any mock/hoist semantics over ESM, including the validation error set. Adapt method-name lists and the auto-import specifier via options. Omit browser wrapModule proxying (`globalThisAccessor`) and redistribution specifiers unless needed.
