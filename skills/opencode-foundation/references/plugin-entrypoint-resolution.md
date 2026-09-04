<!-- capsule-v2 -->
# Plugin entrypoint resolution — which file do you import for a plugin, and what can go wrong?

**Source:** opencode (Slate-licensed monorepo) @ `dev@4643e65a`; Codebase Memory `opencode`. **Question:** How does opencode turn a plugin spec + target into the exact module to `import()`, for both npm packages and local file paths, across server and TUI kinds?

## Entrypoint ladder
**Path/Symbol:** `packages/opencode/src/plugin/shared.ts` (`createPluginEntry`, `resolvePluginEntrypoint`, `resolvePackageEntrypoint`, `resolvePackageFile`, lines 99-236).
**Signature:** `createPluginEntry(spec, target, kind: "server"|"tui"): Promise<PluginEntry>`; entry is a `file://` URL or undefined.
**Data Shape:** npm target = installed package directory (from `Npm.add(spec)`); file target = normalized `file://` URL. Entry selection order: package.json `exports["./"+kind]` → (server only) `"main"` → directory index file (`index.ts|tsx|js|mjs|cjs`) → fall back to the raw target.

### Decisive source
```ts
// shared.ts:89-97 — the jail that makes manifest-driven entrypoints safe
function resolvePackageFile(spec: string, raw: string, kind: string, pkg: PluginPackage) {
  const resolved = resolveExportPath(raw, pkg.dir)
  const root = Filesystem.resolve(pkg.dir)
  const next = Filesystem.resolve(resolved)
  if (!Filesystem.contains(root, next)) {
    throw new Error(`Plugin ${spec} resolved ${kind} entry outside plugin directory`)
  }
  return next
}
```

**Flow:** read `<target>/package.json` (npm: required; file: optional via `.catch(() => undefined)` so bare script files work) → exports map wins → main only for kind==="server" → no manifest/entry: directory index scan for **file** plugins; npm without any entry returns undefined → surfaces as stage "missing" upstream.
**Invariant:** A manifest-declared entry may never escape the plugin directory (`resolvePackageFile` throws on traversal — pinned by `it.live("rejects npm server export that resolves outside plugin directory")`). The TUI kind deliberately does NOT honor `"main"` (main is always a server surface); npm packages with no `./tui` export yield no entry even when a directory exists, while local file dirs get the index-file fallback. Compatibility gate applies ONLY to npm source: `engines.opencode` semver range checked against `InstallationVersion`, skipped entirely for `major === 0` or invalid versions (`checkPluginCompatibility`).
**Probe:** `packages/opencode/test/plugin/loader-shared.test.ts` :302/:362/:421 (npm `./server`, unprefixed `server`, and `main` ladders), :475 (`"does not use npm package exports dot for server entry"`), :529 (traversal rejection), :176 (`"rejects v1 file server plugin without id"`).

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "opencode", query: "createPluginEntry resolvePluginEntrypoint shared.ts", limit: 10 });
```

## Verdict
Adopt the resolution precedence (exports→main→index), the containment jail, and the file-vs-npm asymmetries. Adapt `INDEX_FILES` list and URL normalization to your runtime. Omit Bun-specific globbing details; keep the invariant that manifest entries are jailed but raw path targets are trusted user input.
