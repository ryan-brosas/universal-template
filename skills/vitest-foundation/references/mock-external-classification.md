<!-- capsule-v2 -->
# External classification & id normalization — when does mocking a module id mean "mock an external package" instead of "rewrite a file", and how are ids canonicalized?

**Source:** Vitest (`vitest-dev/vitest`, MIT, `main@cf9176bf`); Codebase Memory `vitest`. **Question:** Given a raw import id and its resolved file, how do I derive the registry key and decide external-vs-internal?

## resolveId external ladder
**Path/Symbol:** `packages/vitest/src/runtime/moduleRunner/bareModuleMocker.ts:BareModuleMocker.resolveId` (:101–148), `isModuleDirectory` (:86–88), `normalizeModuleId` (:357–370), `fixLeadingSlashes` (:391–398), `prefixedBuiltins` (:340–345).
**Signature:** `resolveId(rawId: string, importer?: string): Promise<{ id: string; url: string; external: string | null }>`; `normalizeModuleId(file: string): string`; `getMockPath(dep: string): \`mock:${dep}\``.
**Data Shape:** `external` is `string | null`: the normalized module id when unresolvable or under a module directory (node_modules etc.), else `null`. Registry lookups go through `getMockPath(id)` = `mock:${id}`; `getDependencyMock` applies `fixLeadingSlashes` first because the module runner can hand back `///path` for `file:///path`.

### Decisive source
```ts
// unresolved: keep the raw specifier as both url and external —
// some people mock "vscode" without having it installed
if (!result) {
  const id = normalizeModuleId(rawId)
  return { id, url: rawId, external: id }
}
// external is node_module or unresolved module
const external
  = !isAbsolute(result.file) || this.isModuleDirectory(result.file) ? normalizeModuleId(rawId) : null
const id = normalizeModuleId(result.id)
return { ...result, id, external }

export function normalizeModuleId(file: string): string {
  if (prefixedBuiltins.has(file)) { return file }   // node:test & friends stay whole
  const unixFile = slash(file)
    .replace(/^\/@fs\//, isWindows ? '' : '/')
    .replace(/^node:/, '')
    .replace(/^\/+/, '/')
  return unixFile.replace(/^file:\//, '/')          // not in root → path, not URL
}
```

**Flow:** resolution delegated to injected host resolver inside an OTel span (`vitest.mocker.resolve_id`) → miss ⇒ fallback triple `{id, url: rawId, external}` (mocking uninstalled packages works) → hit ⇒ `external` set iff the file is non-absolute OR sits in a module directory; `node:` prefix stripped; `/@fs/` unwrapped; leading slashes collapsed; drive letters survive via slash-first normalization. The native twin reuses this exact ladder on `fileURLToPath(url)` output.
**Invariant:** `external !== null` routes mock registration toward redirect lookup over package `__mocks__` dirs; `null` means file-rewrite semantics. Registry keys are normalized ids wrapped by `mock:` prefix — never raw specifiers. `fixLeadingSlashes` must run before getById or `file:///x` entries miss their `//x` twins. `node:test`, `node:sea`, `node:sqlite` (mandatory-prefix builtins that collide with `$bare_import` names) are exempt from prefix-stripping.
**Probe:** behavior pinned end-to-end by `test/e2e/test/mocking.test.ts` virtual-module cases (:181/:226) and `test/e2e/fixtures/no-module-runner/test/manual-mock.test.ts` ("builtin node modules are mocked", "deps in node_modules are mocked"). Coverage caveat: no unit test isolates normalizeModuleId; probe is e2e-level.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "vitest", query: "resolveId external normalizeModuleId fixLeadingSlashes prefixedBuiltins", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-signal external test (absolute path + module-directory membership) with the unresolved-id fallback, and the normalization order (slash → @fs → node: → collapse → file://). Adapt the module-directory list and the builtin allowlist to your host's runtime. Omit the OTel span wrapper unless your host carries tracing.
